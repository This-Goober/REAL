---
reel: Transformer math in 30 seconds
target: 30s
aspect: 9:16
---

## hook

Cold open on the formula itself, then the question. Fast; this is the densest beat.

<show image of the attention formula softmax of Q K transpose over root d times V, white on black, large, centred, nothing else in frame>
<Every transformer is built on one line of math. Here it is in thirty seconds.>
<caption: one line>

## three matrices

Calm, one idea per visual. The three colours must stay consistent for the rest of the reel.

<For every token you make three vectors: a query, a key and a value. Same input, three different weight matrices.>
<show image of a single token vector on the left and three arrows fanning out to a blue Q vector, a green K vector and an orange V vector, each labelled, flat vector-art style, dark background>
<caption: Q · K · V>

## scores

<Dot each query with every key. Big number means pay attention to that token.>
<video clip of an animated grid of tokens where one query row lights up and the dot products with every key fill in one by one as numbers, blue times green, dark background, about four seconds ~4s>

## softmax

<Divide by root d so the numbers stay sane, then softmax turns them into weights that add to one.>
<show image of a row of raw scores above and the same row after softmax below, bars that sum to one, the largest bar highlighted, dark background, same blue-green palette>
<caption: weights sum to 1>

## payoff

Land on the line and get out. Let the formula sit on screen a beat after the narration ends.

<Those weights mix the values. That weighted sum is attention, and stacking it is the whole model.>
<show image of orange V vectors being blended by the weights into one output vector, the formula from the hook reappearing underneath, dark background>
<caption: that's attention>
