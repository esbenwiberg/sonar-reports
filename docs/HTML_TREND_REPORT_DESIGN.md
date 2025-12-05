# HTML Trend Report Design

## Overview

This document describes the design for an interactive HTML trend report with embedded Chart.js graphs. This will be an alternative output format to the Markdown report, providing interactive visualizations.

## Features

### Interactive Charts
- **Hover tooltips** - Show exact values on hover
- **Zoom and pan** - Explore data in detail
- **Legend toggle** - Click to show/hide data series
- **Responsive** - Adapts to screen size
- **Animations** - Smooth transitions

### Modern UI
- **Clean design** - Professional appearance
- **Color-coded** - Severity-based color scheme
- **Tabbed interface** - Easy navigation between sections
- **Print-friendly** - CSS for printing
- **Dark mode support** - Optional dark theme

## Technology Stack

- **Chart.js 4.x** - Interactive charts library
- **HTML5/CSS3** - Modern web standards
- **Vanilla JavaScript** - No framework dependencies
- **Bootstrap 5** (optional) - Responsive layout
- **Self-contained** - Single HTML file with embedded data

## Chart Types

### 1. Issues Trend Chart
- **Type:** Line chart with multiple series
- **Data Series:** Blocker (red), Critical (orange), Major (yellow)
- **X-axis:** Date timeline
- **Y-axis:** Issue count
- **Features:** Smooth curves, hover tooltips, legend

### 2. Security Trend Chart
- **Type:** Stacked area chart
- **Data Series:** Vulnerabilities, Security Hotspots, Security Issues
- **X-axis:** Date timeline
- **Y-axis:** Count
- **Features:** Filled areas, color gradients, stacked display

### 3. Quality Gate Chart
- **Type:** Bar chart
- **Data:** Pass/Fail status per date
- **Colors:** Green for PASS, Red for ERROR
- **X-axis:** Date timeline
- **Y-axis:** Status (binary)

### 4. Code Coverage Chart
- **Type:** Line chart with target line
- **Data Series:** Actual coverage, Target (80%)
- **X-axis:** Date timeline
- **Y-axis:** Coverage percentage (0-100%)
- **Features:** Dashed target line, filled area under curve

### 5. Quality Ratings Chart
- **Type:** Radar chart
- **Data:** Security, Reliability, Maintainability ratings
- **Scale:** 1-5 (E to A)
- **Features:** Compare current vs previous period

## HTML Structure

The HTML report will have the following main sections:

1. **Header**
   - Project name and key
   - Analysis period
   - Report metadata

2. **Executive Summary**
   - Overall trend indicator
   - Key metrics comparison table
   - Highlights and concerns

3. **Tabbed Navigation**
   - Issues Trend tab
   - Security tab
   - Quality Gate tab
   - Coverage tab
   - Ratings tab

4. **Chart Sections**
   - Each tab contains a canvas element for Chart.js
   - Analysis text below each chart
   - Key observations and insights

5. **Recommendations**
   - Prioritized action items
   - Effort estimates
   - Expected impact

6. **Detailed Metrics Table**
   - Complete historical data
   - Sortable columns
   - Filterable rows

## Styling Approach

### Color Scheme
- **Primary:** #0288d1 (Blue)
- **Danger:** #d32f2f (Red)
- **Warning:** #f57c00 (Orange)
- **Success:** #4caf50 (Green)
- **Background:** #ffffff (White)
- **Text:** #333333 (Dark Gray)

### Layout
- **Max width:** 1200px centered
- **Padding:** 20px
- **Card-based sections** with shadows
- **Responsive breakpoints** for mobile

### Typography
- **Font:** System fonts (San Francisco, Segoe UI, Roboto)
- **Headings:** Bold, color-coded
- **Body:** 16px, 1.6 line height
- **Code:** Monospace font

## Data Embedding Strategy

All report data will be embedded directly in the HTML file as a JavaScript object. This makes the report:
- Self-contained (no external data files)
- Portable (single file to share)
- Offline-capable (works without internet)

The data structure will include:
- Project metadata
- Timeline data points (all metrics per date)
- Summary statistics
- Recommendations
- Trend calculations

## Interactive Features

### Tab Switching
- Click tabs to switch between chart views
- Smooth fade-in animations
- Active tab highlighting
- URL hash support for deep linking

### Chart Interactions
- Hover over data points for exact values
- Click legend items to show/hide series
- Zoom and pan on charts (optional)
- Export chart as image (optional)

### Table Features
- Sort by any column
- Filter by date range
- Search functionality
- Export to CSV (optional)

## Responsive Design

### Desktop (>1200px)
- Full-width charts
- Side-by-side comparisons
- All features visible

### Tablet (768px-1200px)
- Stacked layout
- Slightly smaller charts
- Collapsible sections

### Mobile (<768px)
- Single column layout
- Simplified charts
- Touch-friendly controls
- Hamburger menu for tabs

## Print Optimization

When printing the HTML report:
- Remove interactive elements (tabs, buttons)
- Show all charts on separate pages
- Black and white friendly colors
- Page breaks between sections
- Header/footer with page numbers

## Implementation Plan

### Phase 1: Template Creation
1. Create HTML template with Jinja2
2. Define CSS styles
3. Set up Chart.js configurations
4. Add tab switching logic

### Phase 2: Data Integration
5. Generate data from trend analysis
6. Embed data as JSON in script tag
7. Initialize charts with data
8. Populate tables and text

### Phase 3: Interactivity
9. Add event listeners for tabs
10. Implement chart interactions
11. Add table sorting/filtering
12. Test responsive behavior

### Phase 4: CLI Integration
13. Add `--format html` option to trend command
14. Support `--format both` for dual output
15. Add configuration options
16. Test and validate

## CLI Usage

```bash
# Generate HTML trend report
python -m sonar_reports trend --reports-dir ./reports --format html

# Generate both Markdown and HTML
python -m sonar_reports trend --reports-dir ./reports --format both

# Custom output location
python -m sonar_reports trend --reports-dir ./reports --format html --output ./trends/report.html
```

## Configuration Options

Add to config file:

```yaml
trend:
  html:
    theme: "light"           # light or dark
    chart_height: 400        # pixels
    enable_zoom: true        # allow chart zoom
    enable_export: true      # allow chart export
    show_animations: true    # chart animations
    color_scheme: "default"  # default or custom
```

## Benefits of HTML Format

1. **Interactive** - Users can explore data dynamically
2. **Self-contained** - Single file with everything embedded
3. **Shareable** - Easy to email or host
4. **Professional** - Modern, polished appearance
5. **Responsive** - Works on all devices
6. **Print-friendly** - Optimized for printing
7. **Offline** - No internet required after loading
8. **Accessible** - Screen reader compatible

## Comparison: HTML vs Markdown

| Feature | Markdown + PNG | HTML + Chart.js |
|---------|----------------|-----------------|
| Interactive | ❌ No | ✅ Yes |
| File Count | Multiple (MD + images) | Single file |
| File Size | Larger (PNG images) | Smaller (vector) |
| Editing | Easy (text editor) | Moderate (HTML) |
| Sharing | Multiple files | Single file |
| Printing | Good | Excellent |
| Mobile | Good | Excellent |
| Offline | ✅ Yes | ✅ Yes |

## Future Enhancements

1. **Export Options**
   - Export charts as PNG/SVG
   - Export data as CSV/JSON
   - Print to PDF

2. **Advanced Filtering**
   - Date range selector
   - Metric selector
   - Comparison mode

3. **Customization**
   - Custom color schemes
   - Logo upload
   - Custom branding

4. **Collaboration**
   - Add comments
   - Share specific views
   - Embed in dashboards

## Dependencies

Required for HTML report generation:

```
chart.js: Loaded from CDN (no installation needed)
jinja2: Already in requirements.txt
```

No additional Python dependencies required!

## Example Output Structure

```
reports/
├── trend-report.md          # Markdown version with PNG graphs
├── trend-report.html        # Interactive HTML version
└── graphs/                  # PNG images (for Markdown)
    ├── issues_trend.png
    ├── security_trend.png
    ├── quality_gate.png
    ├── coverage_trend.png
    └── ratings_trend.png
```

## Next Steps

1. Review this HTML design
2. Decide on format priorities (Markdown first, then HTML?)
3. Switch to Code mode to implement
4. Start with Markdown + PNG implementation
5. Add HTML format as enhancement

---

The HTML format provides a modern, interactive experience while the Markdown format offers simplicity and ease of editing. Both formats can be generated from the same trend data, giving users flexibility in how they view and share reports.