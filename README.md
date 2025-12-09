# Dorkwright - Google Dorking Tool

**Dorkwright** is a powerful Python-based Google dorking utility that automates the extraction of file links from Google search results and optionally downloads them.
It uses **Playwright** for browser automation and includes CAPTCHA handling, progress indicators, and a clean CLI interface.

---

## Features

* Automated Google dorking (search scraping)
* Extracts file URLs (PDF, DOC, XLS, etc.)
* Optional automated file downloading
* CAPTCHA-aware (waits for user to solve)
* Saves results to an output file
* Bulk download support
* Proxy support for downloads
* FlareSolverr integration for bypassing Cloudflare protection
* Fast and Playwright-powered

---

## Usage

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                          DORKWRIGHT - Google Dorker                           ║
║         Extract file links from Google search results and download them       ║
╚═══════════════════════════════════════════════════════════════════════════════╝

options:
  -h, --help            show this help message and exit
  -q, --query QUERY     Google search query (e.g., "site:example.com filetype:doc")
  -p, --pages N         Maximum number of result pages to scrape (default: 10)
  -d, --delay SECONDS   Delay between page requests to avoid CAPTCHA (default: 3)
  -o, --output FILE     Output file for extracted links (default: file_links.txt)
  --download            Download files after extracting links
  --download-dir DIR    Directory to save downloaded files (default: downloads)
  --input-file FILE     Input file with URLs to download (skip search if provided)
  --proxy URL           Proxy server URL (e.g., http://127.0.0.1:8080)
  --flaresolverr URL    FlareSolverr endpoint for bypassing Cloudflare
```

---

## Examples

### **Search and save links**

```bash
dorkwright.py -q "site:example.com filetype:doc OR filetype:docx OR filetype:dot"
dorkwright.py -q "site:example.com filetype:pdf" -p 5 -o results.txt
```

### **Search and immediately download**

```bash
dorkwright.py -q "site:example.com filetype:doc" --download --download-dir downloads
```

### **Download from existing file list**

```bash
dorkwright.py --input-file file_links.txt --download-dir my_files
```

### **Download with proxy**

```bash
# Using HTTP proxy
dorkwright.py --input-file file_links.txt --proxy http://127.0.0.1:8080

# Using SOCKS5 proxy
dorkwright.py --input-file file_links.txt --proxy socks5://127.0.0.1:1080
```

### **Download with FlareSolverr (Cloudflare bypass)**

```bash
# Download from existing file using FlareSolverr
dorkwright.py --input-file file_links.txt --flaresolverr http://localhost:8191

# Search and download with FlareSolverr
dorkwright.py -q "site:example.com filetype:pdf" --download --flaresolverr http://localhost:8191
```

---

## Installation

```bash
git clone https://github.com/San-Tus/Dorkwright
cd Dorkwright
python -m venv .venv
```

Activate the virtual environment:

| OS              | Command                     |
| --------------- | --------------------------- |
| **Windows**     | `.venv\Scripts\activate`    |
| **Linux/macOS** | `source .venv/bin/activate` |

Install required packages:

```bash
pip install -r requirements.txt
playwright install chromium
```

---

## FlareSolverr Setup (Optional)

FlareSolverr is a proxy server that solves Cloudflare challenges, allowing you to download files from Cloudflare-protected sites.

For installation and setup instructions, follow the official documentation:
https://github.com/FlareSolverr/FlareSolverr

---

## Running the Script

```bash
python dorkwright.py -h
```

Example real-world usage:

```bash
python dorkwright.py -q "site:gchq.gov.uk filetype:doc OR filetype:docx OR filetype:xls OR filetype:xlsx OR filetype:pdf" -p 10 --download --download-dir GCHQ
```

---

## Sample Output (Scraping + CAPTCHA Handling)

```
Searching Google for: site:gchq.gov.uk filetype:doc OR filetype:docx OR filetype:xls OR filetype:xlsx OR filetype:pdf
Max pages: 10
Delay between pages: 3s

Searching page 1...

============================================================
CAPTCHA DETECTED!
Please solve the CAPTCHA in the browser window.
Press ENTER here when done...
============================================================
```

Found links appear as:

```
Found: https://www.gchq.gov.uk/files/CheltScienceFestivalTranscript.pdf
Found: https://www.gchq.gov.uk/files/NLCChallenge1_WT.pdf
...
```

---

## Final List of Extracted URLs

```
============================================================
Found 77 unique file links:
============================================================
https://www.gchq.gov.uk/files/2020%20Christmas%20Card%20Solution.pdf
https://www.gchq.gov.uk/files/2020%20Christmas%20Card.pdf
https://www.gchq.gov.uk/files/2023%20GCHQ%20Christmas%20Challenge.pdf
https://www.gchq.gov.uk/files/2024%20Combined%20Pay%20Gap%20External%20-%20Updated.pdf
https://www.gchq.gov.uk/files/Answers.pdf
...
Saved 77 links to file_links.txt
```

## Automated Download Output

When `--download` is enabled:

```
Starting downloads...

Found 77 URLs to download
Saving to directory: GCHQ

  ✓  2020 Christmas Card Solution.pdf                       3.30 MB
  ✓  2020 Christmas Card.pdf                                2.45 MB
  ✓  2023 GCHQ Christmas Challenge.pdf                      6.15 MB
  ✓  2024 Combined Pay Gap External - Updated.pdf         489.67 KB
  ✓  Answers.pdf                                         1016.25 KB
...
```

---

## Download Statistics Example

```
================================================================================
                              DOWNLOAD STATISTICS
================================================================================
  Total files processed:     77
  Successfully downloaded:   77
  Failed downloads:          0
  Total size:                261.16 MB
  Time elapsed:              35.15s
  Average speed:             7.43 MB/s

  File types downloaded:
    .pdf       :  77 files
================================================================================

```
