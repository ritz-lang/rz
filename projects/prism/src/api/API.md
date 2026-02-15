# Prism Client API

This document defines the contract between Prism and its clients (primarily Iris).

## Overview

Prism provides a rendering API that clients use to:
1. Create surfaces for drawing
2. Organize surfaces into a layer tree (for transforms, opacity, clipping)
3. Issue drawing commands (rects, lines, paths, text, images)
4. Receive input events

## Quick Start

```ritz
import prism.api { PrismClient, ClientConfig, DrawContext, SurfaceConfig, LayerConfig }
import prism.api { Rect, Color, Point }

fn main() -> i32
    # Connect to Prism
    let config = ClientConfig.new(800, 600)
    let client = PrismClient.connect(config).unwrap()

    # Create a surface for drawing
    let surface = client.create_surface(SurfaceConfig.new(800, 600))

    # Attach surface to root layer
    client.attach_surface(client.root_layer(), surface)

    # Drawing loop
    loop
        # Handle events
        let events = client.poll_events()
        for event in events
            match event
                WindowEvent.Close => break
                _ => ()

        # Draw
        var ctx = client.begin_draw(surface)
        ctx.fill_rect(Rect.new(0, 0, 800, 600), Color.rgb(30, 30, 30))
        ctx.fill_rect(Rect.new(100, 100, 200, 150), Color.rgb(100, 150, 200))

        # Submit frame
        client.submit_draw(ctx, Vec<Rect>.new())
        client.submit_frame()

    client.disconnect()
    0
```

## Core Types

### PrismClient

Main interface for connecting to Prism.

```ritz
pub struct PrismClient

impl PrismClient
    # Connect to the display server
    pub fn connect(config: ClientConfig) -> Result<PrismClient, ClientError>

    # Disconnect gracefully
    pub fn disconnect(self:&)

    # Surface management
    pub fn create_surface(self:&, config: SurfaceConfig) -> SurfaceId
    pub fn resize_surface(self:&, id: SurfaceId, width: u32, height: u32)
    pub fn destroy_surface(self:&, id: SurfaceId)

    # Layer management
    pub fn create_layer(self:&, config: LayerConfig) -> LayerId
    pub fn destroy_layer(self:&, id: LayerId)
    pub fn update_layer(self:&, id: LayerId, update: LayerUpdate)
    pub fn attach_surface(self:&, layer: LayerId, surface: SurfaceId)
    pub fn set_layer_parent(self:&, layer: LayerId, parent: LayerId)

    # Drawing
    pub fn begin_draw(self:&, surface: SurfaceId) -> DrawContext
    pub fn submit_draw(self:&, ctx: DrawContext, damage: Vec<Rect>)
    pub fn submit_frame(self:&)

    # Events
    pub fn poll_events(self:&) -> Vec<WindowEvent>
    pub fn wait_events(self:&) -> Vec<WindowEvent>

    # Info
    pub fn window_size(self) -> Size
    pub fn root_layer(self) -> LayerId
```

### DrawContext

Accumulates drawing commands for a surface.

```ritz
impl DrawContext
    # Basic shapes
    pub fn fill_rect(self:&, rect: Rect, color: Color)
    pub fn stroke_rect(self:&, rect: Rect, color: Color, width: f32)
    pub fn fill_rounded_rect(self:&, rect: Rect, radius: f32, color: Color)
    pub fn stroke_rounded_rect(self:&, rect: Rect, radius: f32, color: Color, width: f32)

    # Lines
    pub fn draw_line(self:&, from: Point, to: Point, color: Color, width: f32)

    # Paths (complex shapes)
    pub fn fill_path(self:&, path: Path, color: Color)
    pub fn stroke_path(self:&, path: Path, color: Color, width: f32, style: StrokeStyle)

    # Text (pre-shaped glyphs from Angelo)
    pub fn draw_glyphs(self:&, glyphs: GlyphRun, origin: Point, color: Color)

    # Images
    pub fn draw_image(self:&, image: ImageHandle, dest: Rect)
    pub fn draw_image_rect(self:&, image: ImageHandle, src: Rect, dest: Rect)

    # Gradients
    pub fn fill_linear_gradient(self:&, rect: Rect, start: Point, end: Point, stops: Vec<GradientStop>)
    pub fn fill_radial_gradient(self:&, rect: Rect, center: Point, radius: f32, stops: Vec<GradientStop>)

    # Clipping
    pub fn push_clip(self:&, rect: Rect)
    pub fn pop_clip(self:&)

    # Transforms
    pub fn push_transform(self:&, transform: Transform2D)
    pub fn pop_transform(self:&)

    # Shadows (CSS box-shadow)
    pub fn draw_box_shadow(self:&, rect: Rect, shadow: BoxShadow)
```

### Layers

Layers enable CSS-style compositing effects.

```ritz
pub struct LayerConfig
    width: u32
    height: u32
    x: i32
    y: i32
    opacity: f32
    blend_mode: BlendMode
    scrollable: bool

pub struct LayerUpdate
    position: Option<Point>
    size: Option<Size>
    opacity: Option<f32>
    transform: Option<LayerTransform>
    scroll_offset: Option<Point>
    z_index: Option<i32>
```

Use layers for:
- CSS transforms (rotate, scale, translate)
- Opacity animation
- Fixed/sticky positioning
- Scroll containers
- Canvas/video elements

### Text Rendering

Iris shapes text using Angelo, then passes GlyphRun to Prism.

```ritz
# From Angelo (text shaping)
pub struct GlyphRun
    font_id: u32
    font_size: f32
    glyphs: Vec<ShapedGlyph>
    bounds: Rect

pub struct ShapedGlyph
    glyph_id: u32      # Index in font
    x_offset: f32      # Position offset
    y_offset: f32
    x_advance: f32     # Advance to next glyph
    y_advance: f32
    cluster: u32       # For cursor positioning
```

Workflow:
1. Iris calls Angelo to shape text → gets `GlyphRun`
2. Iris calls `draw_glyphs(glyphs, origin, color)`
3. Prism renders the glyphs (rasterizes from font atlas)

### Events

```ritz
pub enum WindowEvent
    Key(KeyEvent)
    MouseMove(MouseMoveEvent)
    MouseButton(MouseButtonEvent)
    Scroll(ScrollEvent)
    Resize(u32, u32)
    Close
    Focus(bool)

pub struct KeyEvent
    code: KeyCode
    modifiers: Modifiers
    pressed: bool
    repeat: bool

pub struct MouseMoveEvent
    x: i32
    y: i32
    dx: i32
    dy: i32
```

## Damage Tracking

For optimal performance, track which regions changed:

```ritz
var damage = Vec<Rect>.new()
damage.push(Rect.new(100, 100, 200, 150))  # Only this area changed
client.submit_draw(ctx, damage)
```

Prism will only composite damaged regions.

## Layer Tree Example

```ritz
# Root layer (fullscreen)
let root = client.root_layer()

# Scroll container
let scroll_layer = client.create_layer(
    LayerConfig.new(800, 2000)  # Tall content
        .at(0, 0)
        .scrollable()
)
client.set_layer_parent(scroll_layer, root)

# Fixed header (doesn't scroll)
let header_layer = client.create_layer(
    LayerConfig.new(800, 60)
        .at(0, 0)
)
client.set_layer_parent(header_layer, root)

# Content surface attached to scroll layer
let content_surface = client.create_surface(SurfaceConfig.new(800, 2000))
client.attach_surface(scroll_layer, content_surface)

# Update scroll position (smooth scrolling)
client.update_layer(scroll_layer,
    LayerUpdate.new().position(0, -scroll_y))
```

## Path Building

For complex shapes (borders with varying radii, custom shapes):

```ritz
let path = PathBuilder.new()
    .move_to(10.0, 0.0)
    .line_to(90.0, 0.0)
    .quad_to(100.0, 0.0, 100.0, 10.0)  # Rounded corner
    .line_to(100.0, 90.0)
    .quad_to(100.0, 100.0, 90.0, 100.0)
    .line_to(10.0, 100.0)
    .quad_to(0.0, 100.0, 0.0, 90.0)
    .line_to(0.0, 10.0)
    .quad_to(0.0, 0.0, 10.0, 0.0)
    .close()
    .build()

ctx.fill_path(path, Color.rgb(100, 100, 200))
```

## Integration with ritzlib.ipc

Transport uses shared memory ringbuffers (from ritzlib.ipc):

```
┌─────────────┐          ┌─────────────┐
│    IRIS     │          │   PRISM     │
│             │          │             │
│  ┌───────┐  │  cmds    │  ┌───────┐  │
│  │ Ring  │──┼──────────┼─▶│ Ring  │  │
│  │ Buf   │  │          │  │ Buf   │  │
│  └───────┘  │          │  └───────┘  │
│             │  events  │             │
│  ┌───────┐  │◀─────────┼──┌───────┐  │
│  │ Ring  │  │          │  │ Ring  │  │
│  │ Buf   │  │          │  │ Buf   │  │
│  └───────┘  │          │  └───────┘  │
└─────────────┘          └─────────────┘
```

Commands are serialized DrawCommand enums. Events are serialized WindowEvent enums.

## Remote Display

The protocol is designed to work over SSH tunneling. All commands use handles/IDs (no pointers). Large data (images, buffers) uses shared memory or chunked transfer.
