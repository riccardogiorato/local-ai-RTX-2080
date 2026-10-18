# Q2_0 vs IQ3_XXS side-by-side (temp 0)

## logic
**prompt:** A bat and a ball cost 1.10 EUR in total. The bat costs 1.00 EUR more than the ball. How much does the ball cost? Reply with the number and one line of justification.
### q2_0 (2.4 s)

0.10 EUR
Let the ball cost x, then the bat costs x + 1.00, so x + (x + 1.00) = 1.10, which simplifies to 2x = 0.10, meaning x = 0.10.

### iq3_xxs (2.8 s)

0.10 EUR
Let the ball cost x, so the bat costs x + 1.00; x + (x + 1.00) = 1.10 implies 2x = 0.10, so x = 0.10.

## logic2
**prompt:** If all Bloops are Razzies and all Razzies are Lazzies, are all Bloops definitely Lazzies? Also state the inverse claim's truth: are all Lazzies definitely Bloops?
### q2_0 (3.0 s)

Yes, all Bloops are definitely Lazzies. This follows from the transitive property of set inclusion: if the set of Bloops is a subset of Razzies, and the set of Razzies is a subset of Lazzies, then the set of Bloops is necessarily a subset of Lazzies.

No, all Lazzies are not definitely Bloops. The inverse claim is false because the relationship is not symmetric; Lazzies may include elements that are not Razzies or Bloops.

### iq3_xxs (1.8 s)

Yes, all Bloops are definitely Lazzies.

No, all Lazzies are not definitely Bloops.

## codebug
**prompt:** Find the bug and output ONLY the corrected function:
```python
def counters(n):
    fns = []
    for i in range(n):
        fns.append(lambda: i)
    return fns
```
### q2_0 (1.6 s)

```python
def counters(n):
    fns = []
    for i in range(n):
        fns.append(lambda i=i: i)
    return fns
```

### iq3_xxs (2.1 s)

```python
def counters(n):
    fns = []
    for i in range(n):
        fns.append(lambda i=i: i)
    return fns
```

## codebug2
**prompt:** This JS rate limiter has a race; explain the race in one sentence and output the corrected code:
```js
let tokens = 0;
function allow() { if (tokens > 0) { tokens--; return true; } return false; }
set
### q2_0 (3.2 s)

The race condition occurs because `setInterval` and `allow()` can interleave in a way that allows multiple concurrent calls to decrement `tokens` below zero or bypass the check, leading to inconsistent state.

Corrected code:
```js
let tokens = 0;
function allow() {
  if (tokens > 0) {
    tokens--;
    return true;
  }
  return false;
}
setInterval(() => {
  tokens = 5;
}, 1000);
```

### iq3_xxs (5.4 s)

The race condition occurs because `tokens` is a shared mutable variable accessed without synchronization, allowing concurrent calls to `allow()` to read the same value before decrementing, potentially allowing more requests than the limit.

```js
let tokens = 0;
let isRefilling = false;

function allow() {
  if (tokens > 0) {
    tokens--;
    return true;
  }
  return false;
}

setInterval(() => {
  if (!isRefilling) {
    isRefilling = true;
    tokens = 5;
    isRefilling = false;
  }
}, 1000);
```

## codehard
**prompt:** Implement a function is_bipartite(graph) in Python that detects whether an undirected graph is 2-colorable, handles disconnected components, and does not mutate the input.
### q2_0 (6.2 s)

```python
def is_bipartite(graph):
    """
    Detect whether an undirected graph is 2-colorable (bipartite).
    
    Args:
        graph: A list of lists where graph[i] contains the neighbors of node i.
               Nodes are numbered 0 to len(graph)-1.
    
    Returns:
        True if the graph is bipartite, False otherwise.
    """
    n = len(graph)
    if n == 0:
        return True
    
    # color[i] = 0 means uncolored, 1 or 2 are the two colors
    color = [0] * n
    
    for start in range(n):
        if color[start] != 0:
            continue
        
        # BFS from this uncolored node
        queue = [start]
        color[start] = 1
        
        while queue:
            node = queue.pop(0)
            for neighbor in graph[node]:
                if color[neighbor] == 0:
                    color[neighbor] = 3 - color[node]  # flip 1->2, 2->1
                    queue.append(neighbor)
                elif color[neighbor] == color[node]:
                    return False
    
    return True
```

### iq3_xxs (6.7 s)

```python
def is_bipartite(graph):
    """
    Detect whether an undirected graph is 2-colorable (bipartite).
    
    Args:
        graph: A dictionary mapping each node to a list of its neighbors.
               The graph is assumed to be undirected.
    
    Returns:
        True if the graph is bipartite, False otherwise.
    """
    # color: 0 = uncolored, 1 = color A, -1 = color B
    color = {}
    
    for node in graph:
        if node in color:
            continue
        
        # Start BFS/DFS from this node (handles disconnected components)
        color[node] = 1
        stack = [node]
        
        while stack:
            current = stack.pop()
            for neighbor in graph[current]:
                if neighbor not in color:
                    color[neighbor] = -color[current]
                    stack.append(neighbor)
                elif color[neighbor] == color[current]:
                    return False
    
    return True
```

## math
**prompt:** A factory's output doubles every 3 days. It starts at 8 units. After how many full days does it first exceed 1000 units? Show the calculation in one line.
### q2_0 (2.7 s)

8 * 2^(d/3) > 1000 => 2^(d/3) > 125 => d/3 > log2(125) ≈ 6.97 => d > 20.91 => 21

### iq3_xxs (3.0 s)

8 * 2^(d/3) > 1000 => 2^(d/3) > 125 => d/3 > log2(125) ≈ 6.966 => d > 20.898 => 21 days

## italiano
**prompt:** Spiega in italiano, in massimo 4 frasi, la differenza tra quantizzazione 2-bit e 3-bit per un modello linguistico, e quando conviene l'una o l'altra.
### q2_0 (3.9 s)

La quantizzazione 2-bit comprime drasticamente il modello, riducendo la memoria e aumentando la velocità, ma introduce spesso una significativa perdita di accuratezza e instabilità. La quantizzazione 3-bit offre un miglior equilibrio, mantenendo una qualità superiore rispetto al 2-bit pur consumando più risorse. Conviene usare il 2-bit quando l'hardware è molto limitato o si privilegia la velocità a scapito della precisione. Conviene usare il 3-bit quando si necessita di un compromesso accettabile tra performance e affidabilità del modello.

### iq3_xxs (6.0 s)

La quantizzazione 2-bit comprime i pesi del modello in soli 4 valori discreti, riducendo drasticamente memoria e costi computazionali rispetto alla 3-bit, che utilizza 8 valori e offre una maggiore fedeltà ai pesi originali. La 2-bit è ideale per dispositivi con risorse estremamente limitate o quando la velocità di inferenza è prioritaria, accettando un degrado significativo delle prestazioni. La 3-bit rappresenta un compromesso migliore, mantenendo una qualità accettabile per la maggior parte dei task generativi su hardware con memoria moderata. In sintesi, si preferisce la 2-bit per l'efficienza estrema e la 3-bit quando è necessario bilanciare compressione e accuratezza del modello.

## idiom
**prompt:** Translate to Italian and briefly explain the trap: 'The data pipeline is a double-edged sword.'
### q2_0 (4.3 s)

**Traduzione:**
"La pipeline dei dati è un'arma a doppio taglio."

**Spiegazione della trappola:**
La frase è ambigua perché "double-edged sword" (arma a doppio taglio) implica che la pipeline dei dati ha sia vantaggi significativi (efficienza, automazione, insights) sia rischi o svantaggi gravi (vulnerabilità a errori, complessità, costi, sicurezza). La trappola sta nel fatto che molti interpretano "pipeline dei dati" come un concetto puramente positivo o neutro, mentre la metafora avverte che la sua implementazione può avere conseguenze negative se non gestita con attenzione.

### iq3_xxs (7.5 s)

**Traduzione:**
"La pipeline di dati è un'arma a doppio taglio."

**Spiegazione della trappola:**
La trappola risiede nell'ambiguità del termine "double-edged sword" (arma a doppio taglio). In italiano, questa espressione è un'idioma consolidato che indica qualcosa che ha sia vantaggi significativi che rischi o svantaggi gravi. Tuttavia, nel contesto tecnico di una "data pipeline", potrebbe essere frainteso come un problema puramente negativo o come una metafora troppo generica. La "trappola" è che l'espressione suggerisce che la pipeline stessa è intrinsecamente pericolosa o dannosa, mentre in realtà il rischio dipende dall'implementazione, dalla governance e dall'uso che se ne fa. Una pipeline ben progettata è uno strumento neutro; il "doppio taglio" emerge solo se non gestita correttamente (es. dati sporchi, sicurezza insufficiente, costi elevati).

## doc-reading
**prompt:** From these meeting notes, answer precisely: Meeting notes, ACME Corp, Q3 planning.
- Attendance: Ravi (infra), Giulia (payments), Marianne (security), Paul (data).
- Decision 1: payments API v2 ships 
### q2_0 (1.8 s)

3.1, 2.8, Nov 30

### iq3_xxs (2.1 s)

3.1, 2.8, neither

## doc-inference
**prompt:** Same meeting notes: Meeting notes, ACME Corp, Q3 planning.
- Attendance: Ravi (infra), Giulia (payments), Marianne (security), Paul (data).
- Decision 1: payments API v2 ships Nov 12, after the PCI au
### q2_0 (2.1 s)

Ravi most plausibly runs the incident rotation (as the infra owner of the migration), and Giulia's objection must be answered first.

### iq3_xxs (2.3 s)

Giulia most plausibly runs the rotation, and Ravi's objection must be answered first.

## constraints
**prompt:** Write exactly three sentences about a GPU's memory bandwidth. Constraints: sentence 2 must contain a number, sentence 3 must not contain the letter 'e' anywhere, and NO bullet points.
### q2_0 (1.9 s)

A GPU uses memory bandwidth to move data. The speed is 100 GB/s. RAM flow is fast.

### iq3_xxs (2.3 s)

High bandwidth allows rapid data transfer. 1000 GB/s is a common figure. Fast flow aids gaming.

## selfref
**prompt:** In the exact sentence you are about to write, how many words will there be? Write that sentence so your claim is true.
### q2_0 (1.1 s)

This sentence has six words.

### iq3_xxs (1.2 s)

This sentence has six words.

## algorithm
**prompt:** For an LRU cache with capacity C that has just evicted its oldest key, what is the amortized cost of a single put() in terms of hash-table lookups? One sentence, complexity only.
### q2_0 (1.2 s)

O(1)

### iq3_xxs (1.7 s)

O(1)

## emergent
**prompt:** Give a rule that generalizes all of these: (2,4)->8, (3,5)->15, (4,7)->28, (5,9)->45. Then apply it to (10,13).
### q2_0 (2.9 s)

The rule is: **Multiply the two numbers.**

Verification:
- $2 \times 4 = 8$
- $3 \times 5 = 15$
- $4 \times 7 = 28$
- $5 \times 9 = 45$

Applying to $(10, 13)$:
$10 \times 13 = 130$

**Answer:** 130

### iq3_xxs (4.6 s)

**Rule:**
For a pair $(a, b)$, the result is $a \times b$.

**Verification:**
*   $(2, 4) \rightarrow 2 \times 4 = 8$
*   $(3, 5) \rightarrow 3 \times 5 = 15$
*   $(4, 7) \rightarrow 4 \times 7 = 28$
*   $(5, 9) \rightarrow 5 \times 9 = 45$

**Application:**
For $(10, 13)$:
$$10 \times 13 = 130$$

**Answer:** 130

