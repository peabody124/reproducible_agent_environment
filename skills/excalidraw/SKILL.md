---
name: excalidraw
description: Use when asked to create diagrams, flowcharts, architecture diagrams, wireframes, visual drawings, or .excalidraw files, or to assemble a composite scientific overview figure (rendered chart/3D panels embedded under a vector annotation layer). Generates valid Excalidraw JSON, embeds raster panels, renders to PNG/SVG, and visually verifies the result.
---

# Excalidraw Diagram Generation

Generate Excalidraw diagrams, render them to images, and visually verify the output.

## Setup

**excalirender** (Bun-based standalone binary, no Node.js required):

```bash
curl -fsSL https://raw.githubusercontent.com/JonRC/excalirender/main/install.sh | sh
excalirender --version
```

**Alternative — Docker** (no install):

```bash
docker run --rm -v "$(pwd):/data" -w /data jonarc06/excalirender diagram.excalidraw -o output.png
```

**Fallback — npx** (requires Node.js 18+):

```bash
npx -y @excalidraw/excalidraw-brute-export-cli diagram.excalidraw output.png
```

## Workflow

### Step 1: Generate `.excalidraw` JSON

Write a valid `.excalidraw` file to `scratch/` (or user-specified path). Follow the JSON Format Reference below exactly.

### Step 2: Render to Image

```bash
excalirender scratch/diagram.excalidraw -o scratch/diagram.png
```

Useful flags:
- `-s 2` — 2x scale (sharper)
- `--dark` — dark mode
- `--transparent` — transparent background
- `-o output.svg` — SVG output (use file extension)

### Step 3: Visually Verify

Read the output image with the Read tool to inspect the rendered diagram. Check:
- All elements are visible and properly positioned
- Arrows connect to the correct shapes
- Text is readable and not overlapping
- Layout is balanced and clear
- **Embedded panels show actual pixels, not a blank box** — a `fileId` mismatch renders a
  silent white rectangle (exit 0, correct size, no image). Inspect the panel, not just the file.

For a **composite scientific figure**, also run the design rubric and re-render until it passes:
- A naive viewer can name the main message in ~5 seconds
- There is ONE clear reading path (L→R linear / cycle / parallel-column compare)
- ≤3 accent colors, used semantically
- Box edges and baselines align to a grid with uniform gutters
- All text is readable at the target export size
- No chartjunk (3D, shadows, gradients, stray ticks/legends) that doesn't serve the message

### Step 4: Iterate if Needed

Fix any issues in the `.excalidraw` JSON and re-render. Common fixes:
- Adjust x/y positions to fix overlapping elements
- Increase width/height of shapes containing long text
- Fix arrow `points` coordinates for proper routing
- Add missing `boundElements` entries on shapes that arrows connect to

## Excalidraw JSON Format Reference

### Top-Level Structure

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "https://excalidraw.com",
  "elements": [],
  "appState": {
    "viewBackgroundColor": "#ffffff",
    "gridSize": null
  },
  "files": {}
}
```

### Common Element Properties

Every element shares these base properties:

```json
{
  "id": "rect1",
  "type": "rectangle",
  "x": 100,
  "y": 200,
  "width": 200,
  "height": 80,
  "angle": 0,
  "strokeColor": "#1e1e1e",
  "backgroundColor": "transparent",
  "fillStyle": "solid",
  "strokeWidth": 2,
  "strokeStyle": "solid",
  "roughness": 1,
  "opacity": 100,
  "seed": 1234567,
  "version": 1,
  "versionNonce": 987654,
  "isDeleted": false,
  "groupIds": [],
  "frameId": null,
  "boundElements": null,
  "updated": 1700000000000,
  "link": null,
  "locked": false,
  "roundness": { "type": 3 }
}
```

**Property Reference:**

| Property | Type | Values / Notes |
|----------|------|----------------|
| `id` | string | Unique identifier. Use short strings like `"box1"`, `"arr1"` |
| `type` | string | `"rectangle"`, `"ellipse"`, `"diamond"`, `"text"`, `"arrow"`, `"line"`, `"freedraw"`, `"image"`, `"frame"` |
| `x`, `y` | number | Top-left corner position in canvas pixels |
| `width`, `height` | number | Dimensions in pixels |
| `angle` | number | Rotation in radians (0 = no rotation) |
| `strokeColor` | string | Hex color for border/stroke |
| `backgroundColor` | string | `"transparent"` or hex color for fill |
| `fillStyle` | string | `"solid"`, `"hachure"`, `"cross-hatch"`, `"zigzag"` |
| `strokeWidth` | number | `1` (thin), `2` (normal), `4` (thick) |
| `strokeStyle` | string | `"solid"`, `"dashed"`, `"dotted"` |
| `roughness` | number | `0` (architect/clean), `1` (artist/default), `2` (cartoonist/rough) |
| `opacity` | number | 0-100 |
| `seed` | number | Random int for deterministic rough.js rendering |
| `version` | number | Start at `1` |
| `versionNonce` | number | Random int |
| `isDeleted` | boolean | Always `false` for new elements |
| `groupIds` | array | Array of group ID strings. Elements sharing a `groupId` are grouped |
| `frameId` | string\|null | ID of containing frame element |
| `boundElements` | array\|null | Array of `{"id": "...", "type": "arrow"}` or `{"id": "...", "type": "text"}` |
| `roundness` | object\|null | `{"type": 3}` for rounded corners, `null` for sharp |
| `locked` | boolean | `false` for editable |

### Element Types

#### Rectangle, Ellipse, Diamond

Use the common properties above. Set `type` to `"rectangle"`, `"ellipse"`, or `"diamond"`.

To make a shape a **container for text**, add the text element's ID to `boundElements`:

```json
{
  "id": "box1",
  "type": "rectangle",
  "x": 100, "y": 100, "width": 200, "height": 80,
  "boundElements": [{"id": "text1", "type": "text"}],
  "...common properties..."
}
```

#### Text

Additional properties beyond the common set:

```json
{
  "id": "text1",
  "type": "text",
  "text": "Hello World",
  "fontSize": 20,
  "fontFamily": 1,
  "textAlign": "center",
  "verticalAlign": "middle",
  "containerId": "box1",
  "originalText": "Hello World",
  "autoResize": true,
  "lineHeight": 1.25
}
```

| Property | Values |
|----------|--------|
| `fontSize` | Number in pixels. Common: `16`, `20`, `28`, `36` |
| `fontFamily` | `1` = Excalifont (hand-drawn), `2` = Nunito (sans-serif), `3` = Comic Shanns (code), `4` = Liberation Sans (system) |
| `textAlign` | `"left"`, `"center"`, `"right"` |
| `verticalAlign` | `"top"`, `"middle"` |
| `containerId` | ID of parent shape, or `null` for standalone text |
| `originalText` | Same as `text` (used for undo) |
| `autoResize` | `true` to auto-fit container |
| `lineHeight` | `1.25` (default) |

**Text-in-Container binding**: The text element has `containerId: "box1"` AND the shape has `boundElements: [{"id": "text1", "type": "text"}]`. Both sides must reference each other. When text is inside a container, set the text's `x`, `y`, `width`, `height` to match the container's inner area (Excalidraw recomputes these, but providing reasonable values avoids rendering artifacts).

#### Arrow

Additional properties beyond the common set:

```json
{
  "id": "arr1",
  "type": "arrow",
  "x": 300, "y": 140,
  "width": 200, "height": 0,
  "points": [[0, 0], [200, 0]],
  "startBinding": {
    "elementId": "box1",
    "fixedPoint": [1, 0.5]
  },
  "endBinding": {
    "elementId": "box2",
    "fixedPoint": [0, 0.5]
  },
  "startArrowhead": null,
  "endArrowhead": "arrow",
  "elbowed": false
}
```

| Property | Values |
|----------|--------|
| `points` | Array of `[dx, dy]` relative to element's `x,y`. **First point MUST be `[0, 0]`** |
| `startBinding` | `null` or `{"elementId": "...", "fixedPoint": [fx, fy]}` |
| `endBinding` | Same as startBinding |
| `fixedPoint` | `[0-1, 0-1]` normalized position on target shape. `[0, 0.5]` = left center, `[1, 0.5]` = right center, `[0.5, 0]` = top center, `[0.5, 1]` = bottom center |
| `startArrowhead` | `null`, `"arrow"`, `"bar"`, `"dot"`, `"triangle"`, `"diamond"` |
| `endArrowhead` | Same options as startArrowhead |
| `elbowed` | `false` for curved/straight, `true` for right-angle routing |

**Arrow-Shape binding**: The arrow has `startBinding.elementId: "box1"` AND box1 has `boundElements: [{"id": "arr1", "type": "arrow"}]`. Both sides must reference each other.

**Arrow positioning**: Set the arrow's `x, y` to the start point. Set `width` and `height` to the bounding box of all points. The `points` array is relative to `x, y`, so the first point is always `[0, 0]`.

#### Line

Same as arrow but with `type: "line"`. No `startBinding`/`endBinding`/arrowheads.

```json
{
  "type": "line",
  "points": [[0, 0], [100, 50], [200, 0]],
  "...common properties..."
}
```

#### Frame

Groups elements visually with a labeled border:

```json
{
  "id": "frame1",
  "type": "frame",
  "name": "Backend Services",
  "x": 50, "y": 50, "width": 600, "height": 400,
  "...common properties..."
}
```

Child elements set `"frameId": "frame1"` to belong to the frame.

#### Image (embedded raster panel)

Embeds a rendered PNG/JPG/SVG (a matplotlib chart, a MuJoCo/mesh render, a photo) as a
panel. An embedded image is **two coupled parts**, and the one load-bearing rule is:

> `element.fileId` === the `files`-map **key** === that entry's `.id`. The element holds
> **no pixels**; the bytes live in the `files` entry.

If they don't match (or the `files` entry is missing), excalirender draws a **silent white
box** — exit 0, correct size, no pixels. So Step 3 must inspect the *panel*, not just that
the file rendered.

**Image element** (extras beyond the common base):

| Property | Values |
|----------|--------|
| `fileId` | Hex string; the key into `files`. Use `sha1(bytes).hexdigest()` (40 chars) |
| `status` | `"saved"` for generated files |
| `scale` | `[1, 1]` default; `[-1, 1]` flips horizontally |
| `crop` | `null`, or `{x, y, width, height, naturalWidth, naturalHeight}` for a sub-region |
| `width`/`height` | display box — **set to the image's natural aspect ratio or it stretches** (excalirender fills the box, it does not preserve aspect) |

**Files entry** (top-level `files` map, keyed by `fileId`):

| Property | Values |
|----------|--------|
| `id` | Same as the key and the element's `fileId` |
| `dataURL` | Full `"data:image/png;base64,..."` string **including the prefix** |
| `mimeType` | `"image/png"`, `"image/jpeg"`, or `"image/svg+xml"` |
| `created` | Epoch ms (e.g. `1700000000000`) |

Hand-authoring megabytes of base64 is impractical — generate the pair with this stdlib
helper. Keep PNGs in `scratch/` and reference them by path; never paste base64 into chat.

```python
import base64, hashlib

def embed_image(path, x, y, width, height, mime="image/png"):
    """Return (image_element, files_patch) for a rendered panel. fileId is the
    sha1 of the bytes, so re-embedding an identical panel dedupes."""
    data = open(path, "rb").read()
    file_id = hashlib.sha1(data).hexdigest()
    data_url = f"data:{mime};base64," + base64.b64encode(data).decode()
    element = {
        "id": file_id[:8], "type": "image", "x": x, "y": y,
        "width": width, "height": height, "angle": 0, "strokeColor": "#1e1e1e",
        "backgroundColor": "transparent", "fillStyle": "solid", "strokeWidth": 2,
        "strokeStyle": "solid", "roughness": 0, "opacity": 100, "seed": 42,
        "version": 1, "versionNonce": 1, "isDeleted": False, "groupIds": [],
        "frameId": None, "boundElements": None, "updated": 1700000000000,
        "link": None, "locked": False, "fileId": file_id, "status": "saved",
        "scale": [1, 1], "crop": None,
    }
    files_patch = {file_id: {"mimeType": mime, "id": file_id,
                             "dataURL": data_url, "created": 1700000000000}}
    return element, files_patch
```

Downsample large renders to display resolution before embedding — base64 inflates ~33% and
lands inline in the JSON (and again in SVG export), so a few multi-MB panels make an
unreadable, undiffable file. Keep `.excalidraw` files with embedded panels out of git.

### Color Palette

Use the Excalidraw default palette (Open Color shades):

**Stroke colors** (shade 7-9, saturated):

| Color | Hex |
|-------|-----|
| Black | `#1e1e1e` |
| Red | `#e03131` |
| Pink | `#c2255c` |
| Grape | `#9c36b5` |
| Violet | `#6741d9` |
| Indigo | `#3b5bdb` |
| Blue | `#1971c2` |
| Cyan | `#0c8599` |
| Teal | `#099268` |
| Green | `#2f9e44` |
| Yellow | `#f08c00` |
| Orange | `#e8590c` |

**Background fills** (shade 1-3, pastel):

| Color | Hex |
|-------|-----|
| Red | `#ffc9c9` |
| Blue | `#a5d8ff` |
| Green | `#b2f2bb` |
| Yellow | `#ffec99` |
| Violet | `#d0bfff` |
| Cyan | `#99e9f2` |
| Orange | `#ffd8a8` |
| Gray | `#e9ecef` |

### Grouping

To group elements, assign the same group ID string to their `groupIds` array:

```json
{"id": "a", "groupIds": ["group1"], "..."},
{"id": "b", "groupIds": ["group1"], "..."}
```

Nested groups: `"groupIds": ["innerGroup", "outerGroup"]` (innermost first).

## Diagram Patterns

### Architecture Diagram (Boxes + Arrows)

Layout: horizontal flow, 250px spacing between box centers.

```
[Client]  -->  [API Gateway]  -->  [Service]  -->  [Database]
x=0           x=300               x=600           x=900
```

Each box: `width=200, height=80`. Arrows start at right edge of source (`x+200, y+40`), end at left edge of target (`x, y+40`).

### Flowchart (Decision Diamonds)

Layout: vertical flow, 150px spacing between element centers.

```
     [Start]
        |
   <Decision?>
    /       \
 [Yes]     [No]
```

Diamonds: `width=160, height=100`. Use `fixedPoint: [0.5, 1]` for bottom exit, `[0, 0.5]` and `[1, 0.5]` for side exits.

### Layered Architecture

Layout: vertical stack with frames.

```
+-- Presentation Layer --+
|  [Component] [Component] |
+------------------------+
+-- Business Logic ------+
|  [Service]  [Service]    |
+------------------------+
+-- Data Layer ----------+
|  [Repository] [Cache]   |
+------------------------+
```

Use `frame` elements for each layer, 50px vertical gap between frames.

## Composite scientific figures (rendered panels + annotation)

**This section applies only to composite/overview figures.** A plain architecture diagram
or flowchart ignores all of it.

A scientific overview figure is **rendered raster panels** (matplotlib/plotly charts,
MuJoCo/mesh/point-cloud renders, photos) under a **vector annotation layer** (arrows, panel
labels, callouts, title). Excalidraw is the programmatic layout + annotation layer; **it
does not render the data** — panels are rendered elsewhere and embedded. If *every* panel is
a matplotlib chart, just use matplotlib subfigures/GridSpec instead. Reach for excalidraw
the moment panels are **heterogeneous** (charts + 3D renders + hand annotation).

### Workflow

1. **State the message.** One sentence: the figure's single take-home, and the medium
   (paper column / slide / poster). Every element serves it.
2. **Render each panel separately at final 1:1 size.** Charts: share one `rcParams` style
   block across all panels (sans-serif, fixed linewidth, the figure's hex color cycler),
   `savefig(dpi=300, transparent=True, bbox_inches="tight", pad_inches=0)`. 3D/mesh/MuJoCo:
   hand off to `/efficient-rendering` (RGBA + transparent bg + matte material, so it
   composites with no grey box); overlay-on-video result panels use `/camera-model` for
   intrinsics/extrinsics/units. Keep PNGs in `scratch/`.
3. **Embed** each panel with `embed_image(...)`. Image elements go **first** in `elements[]`
   (lowest z-order) so annotations sit on top.
4. **Lay out + annotate** (the value-add): one `frame` per panel on a shared grid (snap x/y
   to a ~20px module, uniform gutters, equal-size siblings, shared baselines); bold lowercase
   `a`/`b`/`c` labels at a fixed corner offset (+8,+8); arrows along **one** reading
   direction (L→R / cycle / parallel-column compare); a title that asserts the finding.
5. **Render + verify:** `excalirender fig.excalidraw -o fig.png -s 2`, Read the PNG, run the
   Step-3 rubric, iterate.
6. **Export:** prefer **SVG/PDF** (annotations stay vector, only panels are raster —
   publication-safe). Full-figure PNG (`-s 2`+) for drafts/slides.

### Defaults & palette

- **Publication look:** `roughness: 0`, `fillStyle: "solid"`, `fontFamily: 2` (or 4) on all
  text, body labels ≥16px canvas. (`roughness: 1` / Excalifont is for casual sketches only.)
- **DPI × export scale:** embed at the pixel size you want *at export scale s*; set element
  `width ≈ natural/s`; export with matching `-s`. Otherwise source is crisp but output blurs.
- **Color:** ≤3 accent hues; gray (`#1e1e1e` / `#e9ecef`) for everything de-emphasized; one
  hue per concept, reused everywhere that concept appears — feed the *same* hex list to the
  matplotlib cycler and to render colors. Never red+green to distinguish two classes.
- **Multiview:** panels comparing views/methods must share the camera/unit convention from
  `/camera-model` — don't mix mm and m across panels.

### Companion skills (suggest, never auto-install)

Excalidraw does layout/annotation, not data rendering or palette selection. When a figure
needs more, *suggest* a vetted external skill and let the user install it:

| Need | Skill (license) |
|------|-----------------|
| Tufte-styled minimal-ink chart panels | **tufte-data-viz** (caylent, MIT, read-only) |
| Colorblind-safe palette / "what colors?" | **color-expert** (meodai, CC-BY-4.0) |
| Choose & justify a chart from raw data | **SciPilot figure skill** (MIT, local Python) |
| Crisp editorial schematic, no hand-drawn look | **diagram-design** (MIT) |
| Text-diffable infra/architecture diagram | Mermaid / D2 skills |

Vetting bar: permissive license (MIT/CC-BY), real adoption, prefer read-only/no-exec. Avoid
AntV `mcp-server-chart` for unpublished data — by default it POSTs your chart spec to a
hosted server.

## Best Practices

- **IDs**: Use descriptive short strings (`"box_api"`, `"arr_to_db"`, `"text_title"`)
- **Spacing**: 200-300px horizontal gap between connected nodes, 120-150px vertical gap
- **Arrow points**: First point MUST be `[0, 0]`. A horizontal arrow of length 200: `points: [[0, 0], [200, 0]]`
- **Seeds**: Set `seed` to any random integer (e.g., `42`, `999`, `1577544`) for consistent rough.js rendering
- **Bidirectional bindings**: ALWAYS set both the arrow's `startBinding`/`endBinding` AND the shape's `boundElements` array. Missing either side breaks the connection
- **Text sizing**: For text inside containers, set the text element's `width`/`height` smaller than the container (leave ~20px padding each side)
- **Roughness 0**: Use for clean technical diagrams. Use `1` for the classic hand-drawn look
- **File extension**: Always use `.excalidraw` — this is a plain JSON file
- **Output location**: Write diagrams to `scratch/` by default, or user-specified path
