# Pictures and video on Vatan

Reading an image, drawing one, and making a video. Three jobs, three models, one base
URL.

## Running it

```bash
cp .env.example .env
uv sync
uv run python media.py           # reads an image and draws one
uv run python media.py --video   # also makes a video, which costs real money
```

```
reading a picture
  -> Red

drawing a picture
  text: Sure, here is a product photo of a single yellow rubber duck...
  image: duck.png, 844,575 bytes, image/png

making a video (this costs real money and takes a minute)
  operation operations/766964656f...
  video: boat.mp4, 7,783,589 bytes in 61s
```

## Worth knowing

**The test image is a 64x64 solid red square, checked by decoding it.** An earlier
version of this example carried a PNG that was not actually solid red, and the model
answering "multicoloured" was correct while the example looked broken. A fixture you
have not decoded is a test that can pass for the wrong reason.

**An image comes back as a part, not as text.** Ask with `response_modalities` and walk
`candidates[0].content.parts` for `inline_data`. Reading `.text` and wondering where
the picture went is the usual first mistake.

**A video needs a resolution.** It is priced per second AT EACH resolution, and Vatan
will not start a job it cannot price, so it refuses one without. `GET /v1/models`
lists the resolutions each model is priced at.

**A video is an operation, not a reply.** You get an operation back, poll it, and fetch
the bytes when it is done. Minutes, not seconds.

**A failed poll is not a failed job.** Anything on a network for minutes will
occasionally answer 502 while the job carries on rendering. This example tolerates
three in a row before giving up, and prints the operation name so you can come back to
it. A loop that dies on the first bad poll will lose work you have paid for.

**A refusal prints as one line, not a traceback.** Every example here catches
`errors.APIError` and prints what the gateway said. Run out of key budget and you get
"this key has $0.11 left and this request could cost up to $0.34, so it was not sent",
which tells you what to do; the traceback underneath it does not.

**Video is charged when a poll first sees it finished.** A job nobody polls is a job
nobody is charged for, and also one nobody can download.
