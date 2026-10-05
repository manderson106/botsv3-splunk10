# Official BOTS v3 content goes here (not committed)

Splunk publishes the BOTS v3 **questions, answers and hints** on request rather than in the public repo.
Email **bots@splunk.com** to get the download link, then place the three files here:

```
content/ctf_questions.csv
content/ctf_answers.csv
content/ctf_hints.csv
```

Everything in this directory except this README is git-ignored so the answer key is never published by accident.
Point the installer at it with `BOTS_CONTENT_DIR=$PWD/content`, or import later with
`scripts/import_content.py --content-dir content`.
