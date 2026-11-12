# ☀️ SundayGrids Solar Performance Scraper

An automated scraping tool built with **Playwright** and **Python** to extract comprehensive solar performance data (energy production, capacity, estimated and earned credits) from the **SundayGrids** dashboard across multiple projects (`Ara 40`, `Venera 130`, `Soho 195`) and export structured multi-sheet Excel reports.

---

## ✨ Features

* **Multi-Project Automation**: Seamlessly iterates through configured solar projects on your dashboard.
* **Comprehensive Historical Extraction**: Automatically captures:
  * **All-Time / Consolidated Totals** (`Sheet 1`)
  * **Granular Periods** (`Today`, `This Month`) (`Sheet 2`)
  * **Archived Monthly Data** (`Month by Year` breakdown from January to December) (`Sheet 2`)
* **Robust UI Handling**: Handles dynamic drawers, dropdown expansions, modal backdrops, and state cleanups with bulletproof fallback mechanics (Escape keypresses and overlay click-dismissals).
* **Persistent Session Support**: Uses a local Playwright session folder to retain login state across runs.

---

## 🛠️ Prerequisites

* **Python 3.8+**
* **Google Chrome** installed on your machine.

---

## 📦 Installation

1. Clone or download this repository into your local development directory.
2. Install the required Python packages:

```bash
pip install playwright pandas openpyxl
```

3. Initialize Playwright browsers (if not already installed):

```bash
playwright install chromium
```

---

## 🚀 Usage

1. Run the scraper script:

```bash
python3 sundaygrids_scraper.py
```

2. **First-Time Login**: If your session isn't cached, a browser window will open pointing to SundayGrids. Log into your account manually when prompted in the terminal, then press **Enter** to let the script take over.
3. **Output**: Once completed, the tool generates a structured Excel spreadsheet named **`sundaygrids_detailed_report.xlsx`** containing two tabs:
   * **`Consolidated Totals`**: All-time performance metrics per project.
   * **`History & Current Month`**: Detailed `Today`, `This Month`, and historical monthly breakdowns.

---

## 📁 Project Structure

```text
├── sundaygrids_scraper.py          # Main automation script
├── playwright_session/             # Local browser session cache (auto-created)
└── sundaygrids_detailed_report.xlsx # Generated multi-sheet output report
```

---

## ⚙️ Configuration

You can easily modify target projects directly inside `sundaygrids_scraper.py` by editing the `TARGET_PROJECTS` list:

```python
TARGET_PROJECTS = ["Ara 40", "Venera 130", "Soho 195"]
```