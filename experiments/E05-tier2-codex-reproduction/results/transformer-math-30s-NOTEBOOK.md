---
reel: transformer-math-30s independent reference
target: 30s
aspect: 9:16
---

Shortened reference adaptation. Re-expressed for REAL: captions layered with |.
Narration is a supplied synthetic WAV; it must not be re-estimated.

## hook

<Attention starts with one line of math. Here is how it works.>
<video clip of One line. Many connections. #clip01 | show image of caption one line #img01>

## vectors

<Each token becomes a query, a key, and a value, using three learned projections.>
<video clip of Three views of each token. #clip02 | show image of caption Q · K · V #img02>

## scores

<Dot products compare each query with every key.>
<video clip of Compare a query to every key. #clip03 | show image of caption compare tokens #img03>

## softmax

<Divide by the square root of the key dimension, then apply softmax.>
<video clip of Turn scores into weights. #clip04 | show image of caption weights sum to 1 #img04>

## mix

<The weights blend the values into a new vector for each token.>
<video clip of Mix the values. #clip05 | show image of caption weighted sum #img05>

## context

<Transformers add feed-forward layers and residual paths.>
<video clip of Attention adds context. #clip06 | show image of caption one part of a transformer #img06>

## formula

<That is scaled dot-product attention.>
<video clip of That is attention. #clip07 | show image of caption that's attention #img07>
