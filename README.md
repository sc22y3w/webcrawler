## Webcrawler Search Tool

This project crawls `https://quotes.toscrape.com/`, builds an inverted index, saves it to disk, and lets you search the saved index.

### Requirements

Install the dependencies with:

```bash
pip install -r requirements.txt
```

### Build the index

Launch the CLI, then type `build` to crawl the website and save the index with the default settings:

```bash
python -m src.main
```

The CLI uses the built-in crawl settings and writes the index to `data/index.json`.
When the crawl finishes, it prints a message saying the site was scraped and where the index was saved.

### Load the index

Launch the CLI, then type `load` to load the saved index from `data/index.json`:

```bash
python -m src.main
```

This only works after you have run `build` at least once.

### Search the saved index

After loading the index, launch the CLI and type `search` to search the loaded index:

```bash
python -m src.main
```

Then enter your query when prompted.

### Notes

- Search is case-insensitive.
- The crawler respects a 6-second politeness window between successive requests.
- Search results are grouped by relevance, with exact phrase matches shown before broader term matches.

