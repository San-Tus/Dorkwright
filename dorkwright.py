#!/usr/bin/env python3

import argparse
import asyncio
import os
import re
from pathlib import Path
from urllib.parse import urlparse, unquote
from playwright.async_api import async_playwright
import requests
from tqdm import tqdm


async def extract_file_links(query: str, max_pages: int = 10, delay: int = 3):

    file_links = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            viewport={"width": 1600, "height": 900},
            locale="en-US",
        )
        page = await context.new_page()

        for page_num in range(max_pages):
            try:
                # Construct Google search URL
                start = page_num * 10
                search_url = f"https://www.google.com/search?q={query}&start={start}"

                print(f"Searching page {page_num + 1}...", flush=True)
                await page.goto(search_url, wait_until="networkidle", timeout=30000)

                # Handle cookie consent if present
                try:
                    # Look for common Google consent buttons
                    consent_buttons = [
                        'button:has-text("Accept all")',
                        'button:has-text("Reject all")',
                        'button:has-text("I agree")',
                        "#L2AGLb",  # Google's "Accept all" button ID
                        'button[id="W0wltc"]',  # Another common consent button
                    ]

                    for selector in consent_buttons:
                        try:
                            button = page.locator(selector).first
                            if await button.is_visible(timeout=2000):
                                print(f"  Handling cookie consent...", flush=True)
                                await button.click()
                                await page.wait_for_timeout(1000)
                                break
                        except:
                            continue
                except Exception as e:
                    pass  # No consent dialog, continue

                # Wait a bit for dynamic content
                await page.wait_for_timeout(2000)

                # Check for CAPTCHA
                page_content = await page.content()
                if (
                    "recaptcha" in page_content.lower()
                    or "captcha" in page_content.lower()
                ):
                    print("\n" + "=" * 60)
                    print("CAPTCHA DETECTED!")
                    print("Please solve the CAPTCHA in the browser window.")
                    print("Press ENTER here when done...")
                    print("=" * 60 + "\n")
                    input()  # Wait for user to press Enter
                    await page.wait_for_timeout(2000)

                # Extract all links from search results
                links = await page.evaluate(
                    """
                    () => {
                        const anchors = document.querySelectorAll('a');
                        return Array.from(anchors).map(a => a.href);
                    }
                """
                )

                # Filter for direct file links
                for link in links:
                    if is_file_link(link):
                        clean_link = clean_google_url(link)
                        if clean_link:
                            file_links.add(clean_link)
                            print(f"  Found: {clean_link}")

                # Check if there's a "Next" button
                has_next = await page.evaluate(
                    """
                    () => {
                        const nextButton = document.querySelector('a#pnnext');
                        return nextButton !== null;
                    }
                """
                )

                if not has_next:
                    if page_num + 1 < max_pages:
                        print(
                            f"No more pages available. Scraped {page_num + 1} of {max_pages} requested pages."
                        )
                    else:
                        print("Reached last page of results.")
                    break

                # Delay before next page to avoid triggering anti-bot measures
                if page_num < max_pages - 1:
                    print(f"  Waiting {delay} seconds before next page...", flush=True)
                    await page.wait_for_timeout(delay * 1000)

            except Exception as e:
                print(f"Error on page {page_num + 1}: {e}")
                continue

        await browser.close()

    return sorted(list(file_links))


def clean_google_url(url: str) -> str:
    # Google often wraps URLs like: /url?q=https://example.com/file.pdf&sa=...
    if "/url?q=" in url or "/url?url=" in url:
        match = re.search(r"[?&](?:q|url)=([^&]+)", url)
        if match:
            return unquote(match.group(1))

    # If it's already a direct URL
    if url.startswith("http"):
        return url

    return None


def format_size(bytes_size: float) -> str:
    """Convert bytes to human-readable format"""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for Windows/Unix compatibility.
    Removes or replaces invalid characters.
    """
    # Windows forbidden characters: < > : " / \ | ? *
    # Also remove control characters
    invalid_chars = '<>:"|?*'

    for char in invalid_chars:
        filename = filename.replace(char, "_")

    # Replace forward/back slashes with underscores
    filename = filename.replace("/", "_").replace("\\", "_")

    # Remove control characters (ASCII 0-31)
    filename = "".join(char for char in filename if ord(char) >= 32)

    # Trim whitespace and dots from start/end
    filename = filename.strip(". ")

    # Ensure filename is not empty
    if not filename:
        filename = "file"

    # Windows reserved names
    reserved_names = [
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    ]

    name_without_ext = os.path.splitext(filename)[0].upper()
    if name_without_ext in reserved_names:
        filename = "_" + filename

    return filename


def is_file_link(url: str) -> bool:
    """
    Check if URL appears to be a direct file link.
    Uses a heuristic: looks for a file extension (dot followed by 2-5 alphanumeric chars)
    at the end of the path or before query/fragment.
    """
    url_lower = url.lower()
    parsed = urlparse(url_lower)
    path = parsed.path

    # Skip empty paths or paths that end with /
    if not path or path.endswith("/"):
        return False

    # Check if path has a file extension pattern: .xxx at the end or before ? or #
    # Match extensions like .pdf, .docx, .tar.gz, etc.
    # Pattern matches: filename ending with .extension (2-5 chars after the last dot)
    pattern = r"\.[a-z0-9]{2,5}$"

    # Check if path ends with an extension
    if re.search(pattern, path):
        return True

    # Also check the full URL in case extension is before query params or fragments
    # e.g., /file.pdf?download=true
    if re.search(r"\.[a-z0-9]{2,5}[?#]", url_lower):
        return True

    return False


def save_links(links: list, output_file: str):
    with open(output_file, "w", encoding="utf-8") as f:
        for link in links:
            f.write(f"{link}\n")
    print(f"\nSaved {len(links)} links to {output_file}")


def download_files(input_file: str, output_dir: str):
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Read URLs from file
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found.")
        return

    if not urls:
        print(f"No URLs found in {input_file}")
        return

    print(f"Found {len(urls)} URLs to download")
    print(f"Saving to directory: {output_dir}")

    success_count = 0
    failed_count = 0
    total_bytes = 0
    file_types = {}
    import time

    start_time = time.time()

    # Progress bar for overall download progress
    print()  # Space for individual file progress bar above
    pbar_overall = tqdm(
        total=len(urls),
        desc="Overall Progress",
        unit=" file",
        position=1,
        bar_format="{l_bar}{bar:40}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
        colour="green",
        ncols=100,
        leave=False,  # Don't leave the progress bar after completion
    )

    try:
        for idx, url in enumerate(urls, 1):
            filename = None
            try:
                # Download file with progress bar
                response = requests.get(url, timeout=30, stream=True)
                response.raise_for_status()

                # Determine filename from Content-Disposition header if available
                content_disposition = response.headers.get("Content-Disposition", "")
                if content_disposition:
                    # Try to extract filename from Content-Disposition header
                    # Format: attachment; filename="example.pdf" or filename*=UTF-8''example.pdf
                    # First try RFC 5987 encoded filename (filename*=UTF-8''...)
                    filename_match = re.search(
                        r"filename\*=UTF-8''([^;]+)", content_disposition
                    )
                    if filename_match:
                        filename = unquote(filename_match.group(1), encoding="utf-8")
                    else:
                        # Try regular filename parameter
                        filename_match = re.search(
                            r'filename=["\'"]?([^"\'";]+)', content_disposition
                        )
                        if filename_match:
                            # Try to decode if it looks like it's UTF-8 encoded
                            raw_filename = filename_match.group(1).strip("\"'")
                            try:
                                # If the filename is Latin-1 encoded but contains UTF-8 bytes
                                filename = raw_filename.encode("latin-1").decode(
                                    "utf-8"
                                )
                            except (UnicodeDecodeError, UnicodeEncodeError):
                                filename = raw_filename

                # If no filename from headers, extract from URL path
                if not filename:
                    parsed = urlparse(url)
                    # URL-decode the path properly
                    filename = unquote(os.path.basename(parsed.path), encoding="utf-8")

                # Determine correct file extension from Content-Type header
                content_type = (
                    response.headers.get("Content-Type", "")
                    .split(";")[0]
                    .strip()
                    .lower()
                )

                # Map common MIME types to extensions
                mime_to_ext = {
                    "application/pdf": ".pdf",
                    "application/msword": ".doc",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
                    "application/vnd.ms-excel": ".xls",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
                    "application/vnd.ms-powerpoint": ".ppt",
                    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
                    "application/zip": ".zip",
                    "application/x-zip-compressed": ".zip",
                    "text/plain": ".txt",
                    "text/csv": ".csv",
                    "image/jpeg": ".jpg",
                    "image/png": ".png",
                    "image/gif": ".gif",
                }

                # Get extension from content-type if available
                correct_ext = mime_to_ext.get(content_type, "")

                # If we have a filename but it has wrong extension (e.g., .aspx for a PDF)
                if filename and correct_ext:
                    current_ext = os.path.splitext(filename)[1].lower()
                    # Replace extension if current one doesn't match content type
                    if current_ext != correct_ext and current_ext in [
                        ".aspx",
                        ".php",
                        ".jsp",
                        ".cgi",
                        ".asp",
                    ]:
                        base = os.path.splitext(filename)[0]
                        filename = f"{base}{correct_ext}"

                # If still no filename, generate one
                if not filename or "." not in filename:
                    ext = correct_ext if correct_ext else ""
                    filename = f"file_{idx}{ext}"

                # Sanitize filename for filesystem compatibility
                filename = sanitize_filename(filename)

                output_path = os.path.join(output_dir, filename)

                # Handle duplicate filenames
                if os.path.exists(output_path):
                    base, ext = os.path.splitext(filename)
                    counter = 1
                    while os.path.exists(output_path):
                        filename = f"{base}_{counter}{ext}"
                        output_path = os.path.join(output_dir, filename)
                        counter += 1

                # Get file size from headers if available
                total_size = int(response.headers.get("content-length", 0))

                # Progress bar for individual file download
                desc = f"Downloading {filename[:35]}"
                with tqdm(
                    total=total_size,
                    desc=desc,
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                    position=0,
                    leave=False,
                    bar_format="{desc}: {percentage:3.0f}%|{bar:30}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
                    colour="cyan",
                    ncols=100,
                ) as pbar_file:
                    with open(output_path, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                pbar_file.update(len(chunk))

                file_size = os.path.getsize(output_path)
                total_bytes += file_size

                # Track file type
                ext = os.path.splitext(filename)[1].lower()
                if ext:
                    file_types[ext] = file_types.get(ext, 0) + 1

                # Format output with padding for alignment
                pbar_overall.write(
                    f"  ✓  {filename:<50s}  {format_size(file_size):>10s}"
                )
                success_count += 1

            except requests.RequestException as e:
                display_name = filename if filename else url[:50]
                pbar_overall.write(f"  ✗  {display_name:<50s}  FAILED")
                failed_count += 1
            except Exception as e:
                display_name = filename if filename else url[:50]
                pbar_overall.write(f"  ✗  {display_name:<50s}  ERROR")
                failed_count += 1
            finally:
                pbar_overall.update(1)

    finally:
        # Close the progress bar - it will auto-clear because leave=False
        pbar_overall.close()

    # Add a newline for spacing
    print()

    # Calculate statistics
    end_time = time.time()
    elapsed_time = end_time - start_time
    avg_speed = total_bytes / elapsed_time if elapsed_time > 0 else 0

    # Display statistics
    print(f"{'='*80}")
    print(f"{'DOWNLOAD STATISTICS':^80}")
    print(f"{'='*80}")
    print(f"  Total files processed:     {len(urls)}")
    print(f"  Successfully downloaded:   {success_count}")
    print(f"  Failed downloads:          {failed_count}")
    print(f"  Total size:                {format_size(total_bytes)}")
    print(f"  Time elapsed:              {elapsed_time:.2f}s")
    print(f"  Average speed:             {format_size(avg_speed)}/s")

    if file_types:
        print(f"\n  File types downloaded:")
        for ext, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True):
            print(f"    {ext:10s} : {count:3d} file{'s' if count != 1 else ''}")

    print(f"{'='*80}")


async def main():
    parser = argparse.ArgumentParser(
        description="""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                          DORKWRIGHT - Google Dorker                           ║
║         Extract file links from Google search results and download them       ║
╚═══════════════════════════════════════════════════════════════════════════════╝
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
═══════════════════════════════════════════════════════════════════════════════════

USAGE EXAMPLES:

  Search and save links:
  ─────────────────────────────────────────────────────────────────────────────
  %(prog)s -q "site:example.com filetype:doc OR filetype:docx OR filetype:dot"
  %(prog)s -q "site:example.com filetype:pdf" -p 5 -o results.txt

  Search and download immediately:
  ─────────────────────────────────────────────────────────────────────────────
  %(prog)s -q "site:example.com filetype:doc" --download --download-dir downloads

  Download from existing file:
  ─────────────────────────────────────────────────────────────────────────────
  %(prog)s --input-file file_links.txt --download-dir my_files

═══════════════════════════════════════════════════════════════════════════════════
        """,
    )

    # Search options
    parser.add_argument(
        "-q",
        "--query",
        metavar="QUERY",
        help='Google search query (e.g., "site:example.com filetype:doc")\n\n',
    )

    parser.add_argument(
        "-p",
        "--pages",
        metavar="N",
        type=int,
        default=10,
        help="Maximum number of result pages to scrape (default: 10)\n\n",
    )

    parser.add_argument(
        "-d",
        "--delay",
        metavar="SECONDS",
        type=int,
        default=3,
        help="Delay in seconds between page requests to avoid CAPTCHA (default: 3)\n\n",
    )

    # Output options
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        default="file_links.txt",
        help="Output file for extracted links (default: file_links.txt)\n\n",
    )

    # Download options
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download files after extracting links\n\n",
    )

    parser.add_argument(
        "--download-dir",
        metavar="DIR",
        default="downloads",
        help="Directory to save downloaded files (default: downloads)\n\n",
    )

    parser.add_argument(
        "--input-file",
        metavar="FILE",
        help="Input file with URLs to download (skip search if provided)\n\n",
    )

    args = parser.parse_args()

    # Mode 1: Download from existing file
    if args.input_file:
        download_files(args.input_file, args.download_dir)
        return

    # Mode 2: Search and optionally download
    if not args.query:
        parser.error(
            "the following arguments are required: -q/--query (unless using --input-file)"
        )

    print(f"Searching Google for: {args.query}")
    print(f"Max pages: {args.pages}")
    print(f"Delay between pages: {args.delay}s\n")

    # Extract links
    links = await extract_file_links(
        query=args.query, max_pages=args.pages, delay=args.delay
    )

    # Display results
    print(f"\n{'='*60}")
    print(f"Found {len(links)} unique file links:")
    print(f"{'='*60}")
    for link in links:
        print(link)

    # Save to file
    if links:
        save_links(links, args.output)

        # Download if requested
        if args.download:
            print(f"\nStarting downloads...\n")
            download_files(args.output, args.download_dir)
        else:
            print(f"\nYou can download all files with:")
            print(
                f"  python {parser.prog} --input-file {args.output} --download-dir {args.download_dir}"
            )
            print(f"Or with wget:")
            print(f"  wget -i {args.output}")
    else:
        print("\nNo file links found.")


if __name__ == "__main__":
    asyncio.run(main())
