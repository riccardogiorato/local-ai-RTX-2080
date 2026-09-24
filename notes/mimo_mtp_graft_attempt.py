#!/usr/bin/env python3
"""Graft Qwen3.5-9B's embedded MTP head (blk.32.nextn.*) into the MiMo distill GGUF."""
import numpy as np
from gguf import GGUFReader, GGUFWriter
from gguf.constants import GGUFValueType

MIMO = '/home/riccardogiorato/models/mimo-9b/MiMo-V2.6-Distill-Qwen-9B-Q4_K_M.gguf'
BASE9B = '/home/riccardogiorato/models/qwen35-9b-mtp/Qwen3.5-9B-Q4_K_M.gguf'
OUT = '/home/riccardogiorato/models/mimo-9b/MiMo-V2.6-Distill-Qwen-9B-Q4_K_M-plusMTP.gguf'

def nm(x):
    return x.decode() if isinstance(x, bytes) else str(x)

def add_copy(writer, t, name):
    """Copy a reader tensor verbatim.

    Reader t.shape is GGUF ne-order (x-dim first); the writer serializes
    ne reversed from TensorInfo.shape, i.e. TensorInfo.shape must be numpy
    order (rows first). Quantized data must arrive as a uint8 buffer whose
    byte-shape (rows..., bytes/row) the writer converts to element counts.
    """
    ne_shape = tuple(int(d) for d in t.shape)
    numpy_shape = ne_shape[::-1]
    if len(numpy_shape) == 1:
        raw = (t.n_bytes,)
    else:
        rows = int(np.prod(numpy_shape[:-1]))
        bytes_per_row = t.n_bytes // rows
        raw = (*numpy_shape[:-1], bytes_per_row)
    writer.add_tensor(name, np.frombuffer(t.data, dtype=np.uint8, count=t.n_bytes),
                      raw_shape=raw, raw_dtype=t.tensor_type)

mimo = GGUFReader(MIMO)
base = GGUFReader(BASE9B)

arch = mimo.fields['general.architecture'].contents()
print('arch:', repr(arch))

w = GGUFWriter(OUT, arch)

for name, f in mimo.fields.items():
    key = nm(name)
    if key == 'general.architecture':
        continue
    vt = f.types[0]
    if vt == GGUFValueType.ARRAY:
        w.add_array(key, f.contents())
    elif vt == GGUFValueType.STRING:
        w.add_string(key, f.contents())
    else:
        getattr(w, 'add_' + vt.name.lower())(key, f.contents())
print('fields copied:', len(mimo.fields))

# the 4 nextn tensors from the base 9B, verbatim quantized bytes
count = 0
for t in base.tensors:
    name = nm(t.name)
    if 'nextn' in name:
        # MiMo declares block_count=32 (nextn at blk.{count-1}); the 9B GGUF
        # stamps them at blk.32 (its block_count=33). Rename to MiMo's index.
        add_copy(w, t, name.replace('blk.32.nextn', 'blk.31.nextn'))
        print('grafted', name, 'shape', t.shape, 'type', t.tensor_type, 'bytes', t.n_bytes)
        count += 1
assert count == 4, f'expected 4 nextn tensors, got {count}'
w.add_uint32(f'{arch}.nextn_predict_layers', 1)

for t in mimo.tensors:
    add_copy(w, t, nm(t.name))
print('mimo tensors copied:', len(mimo.tensors))

w.write_header_to_file()
w.write_kv_data_to_file()
w.write_tensors_to_file()
w.close()
print('WROTE', OUT)