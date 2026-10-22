#!/usr/bin/env python3
"""Recording reverse proxy for the harness comparison: every harness request to the
local Strata serve goes through here. Bodies land in proxy-out/requests/, per-request
token-usage rows in proxy-out/proxy.jsonl (Strata's own usage for both streamed and
unstreamed calls), and the exact system-prompt token counts are recomputed with the
Swift pack's reference tokenizer.

Usage: python3 proxy.py [port]      (forwards to http://127.0.0.1:8080)
Label the caller first: curl -s http://127.0.0.1:PORT/_label -d '{"harness":"pi"}'
"""
import http.server
import importlib.util
import json
import os
import pathlib
import sys
import threading
import time
import urllib.error
import urllib.request

UPSTREAM = 'http://127.0.0.1:8080'
HERE = pathlib.Path(__file__).resolve().parent
# PROXY_OUT_DIR re-homes the capture dir (used by the claude AG-Bench experiment
# so its rows never mix into the loop-study capture).
OUT = pathlib.Path(os.environ.get('PROXY_OUT_DIR') or HERE / 'proxy-out')
REQDIR = OUT / 'requests'
OUT.mkdir(exist_ok=True, parents=True)
REQDIR.mkdir(exist_ok=True)
LOG = OUT / 'proxy.jsonl'

# the Swift pack's own tokenizer, loaded once (reference implementation, round-trip exact)
_spec = importlib.util.spec_from_file_location(
    'st_tok', '/home/riccardogiorato/Desktop/github/strata-port/tools/strata_tokenizer.py')
st = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(st)
_tokdir = pathlib.Path('/home/riccardogiorato/Desktop/github/strata-port/packs/swift15-iq2xs-gsq/tokenizer')
_ids = json.loads((_tokdir / 'vocab.json').read_text())
_tokens = [None] * len(_ids)
for _t, _i in _ids.items():
    _tokens[_i] = _t
TOKENIZER = st.Tokenizer(_tokens, (_tokdir / 'merges.txt').read_text().splitlines(),
                         json.loads((_tokdir / 'token_type.json').read_text()))

STATE = {'label': 'untagged'}
LOCK = threading.Lock()
_SEQ = [0]

SKIP_HEADERS = {'host', 'content-length', 'accept-encoding', 'connection'}


def ntok(text):
    return len(TOKENIZER.encode(text))


def extract_system(payload):
    """Return the system-instruction text for either API shape."""
    parts = []
    sysv = payload.get('system')
    if isinstance(sysv, str):
        parts.append(sysv)
    elif isinstance(sysv, list):
        parts.extend(b.get('text', '') for b in sysv if isinstance(b, dict))
    for m in payload.get('messages', []):
        if m.get('role') == 'system':
            c = m.get('content')
            if isinstance(c, str):
                parts.append(c)
            elif isinstance(c, list):
                parts.extend(seg.get('text', '') for seg in c if isinstance(seg, dict))
    return '\n'.join(parts)


def harvest_sse(chunks, route):
    """Pull usage + stop reason out of a captured SSE stream."""
    usage, stop = None, None
    for raw_line in chunks:
        line = raw_line.decode('utf-8', 'replace').strip()
        if not line.startswith('data:'):
            continue
        data = line[5:].strip()
        if data == '[DONE]':
            continue
        try:
            obj = json.loads(data)
        except Exception:
            continue
        u = obj.get('usage')
        if u:
            usage = u
        if route.endswith('/chat/completions'):
            for ch in obj.get('choices', []):
                if ch.get('finish_reason'):
                    stop = ch['finish_reason']
        else:  # anthropic SSE
            if obj.get('type') == 'message_start':
                usage = obj.get('message', {}).get('usage') or usage
            if obj.get('type') == 'message_delta':
                stop = obj.get('delta', {}).get('stop_reason') or stop
                d = obj.get('usage')
                if d and usage is None:
                    usage = d
                elif d and usage is not None:
                    usage.update(d)
    return usage, stop


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *a):
        pass

    def _forward_headers(self):
        req = {}
        for k, v in self.headers.items():
            if k.lower() not in SKIP_HEADERS:
                req[k] = v
        return req

    def _pipe(self, resp):
        """Stream an SSE response through while Capturing chunks."""
        self.send_response(resp.status)
        for k, v in resp.headers.items():
            if k.lower() in ('content-length', 'transfer-encoding', 'connection'):
                continue
            self.send_header(k, v)
        self.send_header('Connection', 'close')
        self.end_headers()
        chunks = []
        while True:
            line = resp.readline()
            if not line:
                break
            chunks.append(line)
            try:
                self.wfile.write(line)
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass  # client gone; keep capturing
        self.close_connection = True
        return chunks

    def _relay(self):
        if self.path.startswith('/_label'):
            n = int(self.headers.get('Content-Length', 0) or 0)
            body = self.rfile.read(n) if n else b'{}'
            try:
                STATE['label'] = json.loads(body).get('harness', 'untagged')
            except Exception:
                pass
            msg = b'{"ok":true}'
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)
            return
        n = int(self.headers.get('Content-Length', 0) or 0)
        body = self.rfile.read(n) if n else b''
        path = self.path
        with LOCK:
            _SEQ[0] += 1
            seq = _SEQ[0]
            label = STATE['label']
        try:
            payload = json.loads(body) if body else {}
            if not isinstance(payload, dict):
                payload = {}
        except Exception:
            payload = {}
        req_headers = self._forward_headers()

        stream = bool(payload.get('stream'))
        fwd_body = body
        # make OpenAI-style streams report usage in the final chunk (Strata 0.2.2 supports it)
        if stream and path.endswith('/chat/completions'):
            try:
                so = payload.get('stream_options') or {}
                so['include_usage'] = True
                payload['stream_options'] = so
                fwd_body = json.dumps(payload).encode()
                req_headers['Content-Length'] = str(len(fwd_body))
            except Exception:
                fwd_body = body
        if body and 'Content-Length' not in req_headers:
            req_headers['Content-Length'] = str(len(fwd_body))

        req = urllib.request.Request(UPSTREAM + path, data=fwd_body if body else None,
                                     headers=req_headers, method=self.command)
        t0 = time.time()
        wall = None
        status, chunks, raw = None, None, None
        try:
            resp = urllib.request.urlopen(req, timeout=660)
        except urllib.error.HTTPError as e:
            resp = e
        except Exception as e:
            self.send_response(502)
            self.send_header('Content-Type', 'application/json')
            msg = json.dumps({'proxy_error': str(e)}).encode()
            self.send_header('Content-Length', str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)
            self._row(path, seq, label, payload, None, None, 0.0, 502, 'proxy_error')
            return
        ctype = resp.headers.get('Content-Type', '')
        if stream and 'event-stream' in ctype.lower():
            chunks = self._pipe(resp)
            wall = time.time() - t0
            usage, stop = harvest_sse(chunks, path)
            self._row(path, seq, label, payload, usage, stop, wall, resp.status, chunks)
        else:
            raw = resp.read()
            wall = time.time() - t0
            self.send_response(resp.status)
            for k, v in resp.headers.items():
                if k.lower() in ('content-length', 'transfer-encoding', 'connection'):
                    continue
                self.send_header(k, v)
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            self._row(path, seq, label, payload, None, None, wall, resp.status, None, raw)

    def _row(self, path, seq, label, payload, usage, stop, wall, status,
             chunks=None, raw=None):
        usage = dict(usage or {})
        if raw is not None:
            try:
                obj = json.loads(raw)
                if 'usage' in obj:
                    usage.update(obj['usage'])
                stop = stop or obj.get('stop_reason') or (
                    obj.get('choices') or [{}])[0].get('finish_reason')
            except Exception:
                pass
        system_text = extract_system(payload)
        msgs = payload.get('messages') or []
        tools = payload.get('tools') or []
        prompt = usage.get('prompt_tokens') or usage.get('input_tokens')
        cached = ((usage.get('prompt_tokens_details') or {}).get('cached_tokens')
                  or usage.get('cache_read_input_tokens'))
        creation = usage.get('cache_creation_input_tokens')
        # anthropic: input_tokens counts only uncached; total context = input + creation + read
        if usage.get('input_tokens') is not None and prompt is not None and cached is not None:
            effective = prompt + (creation or 0) + cached
        else:
            effective = prompt
        row = {
            'ts': time.strftime('%H:%M:%S'), 'seq': seq, 'label': label, 'route': path,
            'method': self.command, 'status': status, 'stream': bool(payload.get('stream')),
            'prompt_tokens': prompt,
            'cached_tokens': cached,
            'cache_creation_tokens': creation,
            'effective_prompt_tokens': effective,
            'output_tokens': usage.get('output_tokens') or usage.get('completion_tokens'),
            'stop_reason': stop, 'wall_s': round(wall, 2),
            'n_messages': len(msgs), 'n_roles': [m.get('role') for m in msgs][:4],
            'n_tools': len(tools), 'tool_names': [t.get('name', '?') for t in tools][:24],
            'system_chars': len(system_text), 'system_tokens': ntok(system_text) if system_text else 0,
            'max_tokens': payload.get('max_tokens') or payload.get('max_completion_tokens'),
        }
        with LOCK:
            REQDIR.mkdir(exist_ok=True)
            (REQDIR / f'{seq:03d}.json').write_text(json.dumps(payload, indent=1,
                    ensure_ascii=False, default=str) if payload else '{}')
            with LOG.open('a') as f:
                f.write(json.dumps(row, default=str) + '\n')

    def do_POST(self):
        self._relay()

    def do_GET(self):
        if self.path.startswith('/_label'):
            n = int(self.headers.get('Content-Length', 0) or 0)
            body = self.rfile.read(n) if n else b'{}'
            try:
                STATE['label'] = json.loads(body).get('harness', 'untagged')
            except Exception:
                pass
            msg = b'{"ok":true}'
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)
            return
        req = urllib.request.Request(UPSTREAM + self.path, headers=self._forward_headers())
        try:
            resp = urllib.request.urlopen(req, timeout=120)
        except urllib.error.HTTPError as e:
            resp = e
        except Exception as e:
            self.send_response(502)
            self.send_header('Content-Length', '0')
            self.end_headers()
            return
        raw = resp.read()
        self.send_response(resp.status)
        for k, v in resp.headers.items():
            if k.lower() in ('content-length', 'transfer-encoding', 'connection'):
                continue
            self.send_header(k, v)
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


class Server(http.server.ThreadingHTTPServer):
    daemon_threads = True


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8081
    Server(('127.0.0.1', port), Handler).serve_forever()
