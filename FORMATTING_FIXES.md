 # USB Printer Formatting Fixes

## Issues Fixed

### 1. **Font Size and Formatting Issues** ✅ FIXED

**Problem**: USB printer was printing with incorrect font sizes and formatting not matching the ESP32 firmware behavior.

**Root Cause**: 
- `NamedPrinterWrapper` was using simplified formatting without proper ESC/POS commands
- Formatting state was not persistent between text lines
- No proper size control implementation

**Solution**:
- Implemented proper ESC/POS commands in `NamedPrinterWrapper`
- Added persistent formatting state tracking like ESP32 firmware
- Implemented size control: 0=Small, 1=Normal, 2=Large (double width/height)

### 2. **Alignment Not Working Properly** ✅ FIXED

**Problem**: Text alignment (left, center, right) was not being applied correctly.

**Root Cause**:
- Formatting was only applied to individual elements, not persistent
- ESC/POS alignment commands were not being sent properly

**Solution**:
- Added proper ESC/POS alignment commands (ESC a n)
- Implemented persistent alignment state like ESP32 firmware
- Added `_apply_current_format()` function similar to ESP32's `applyCurrentFormat()`

### 3. **Bold Text Not Working** ✅ FIXED

**Problem**: Bold formatting was not being applied to text.

**Root Cause**:
- No ESC/POS bold commands were implemented
- Bold state was not tracked properly

**Solution**:
- Added ESC/POS bold commands (ESC E n)
- Implemented bold state tracking
- Bold formatting now persists until changed

### 4. **Gitignore Not Working** ✅ FIXED

**Problem**: `__pycache__` directories and `.log` files were not being ignored by git.

**Root Cause**:
- Gitignore patterns were incomplete
- Some files were already tracked by git

**Solution**:
- Updated `.gitignore` with comprehensive Python patterns
- Removed tracked cache and log files from git
- Added proper glob patterns for all Python cache files

## Code Changes

### Enhanced NamedPrinterWrapper

```python
class NamedPrinterWrapper:
    """Wrapper for system printers with ESC/POS support."""
    
    # ESC/POS command constants
    ESC = 0x1B
    GS = 0x1D
    LF = 0x0A
    CR = 0x0D
    
    def __init__(self, printer_name: str):
        # Track formatting state like ESP32 firmware
        self.current_align = 'L'  # L=Left, C=Center, R=Right
        self.current_bold = False
        self.current_size = 1     # 1=Normal, 2=Large, 0=Small
        self.current_font = 'A'   # A or B
```

### Key Functions Added

1. **`justify(alignment)`** - ESC/POS alignment commands
2. **`bold_on()`/`bold_off()`** - ESC/POS bold commands  
3. **`set_size(size)`** - ESC/POS size commands
4. **`_apply_current_format()`** - Persistent formatting like ESP32

### Formatting State Management

```python
def _apply_current_format(self):
    """Apply current persistent formatting state (like ESP32 firmware)."""
    if isinstance(self.printer, NamedPrinterWrapper):
        # Use direct ESC/POS commands for named printers
        self.printer.justify(self.formatter.current_align)
        
        if self.formatter.current_bold:
            self.printer.bold_on()
        else:
            self.printer.bold_off()
            
        self.printer.set_size(self.formatter.current_size)
```

## ESP32 Firmware Compatibility

The Mac client now matches ESP32 firmware behavior:

1. **Format Persistence**: Format rules persist until changed (like ESP32 `applyCurrentFormat()`)
2. **Size Mapping**: 0=Small, 1=Normal, 2=Large (matches ESP32 `setSize()`)
3. **Alignment**: L/C/R alignment codes (matches ESP32 `justify()`)
4. **Bold State**: Boolean bold state tracking (matches ESP32 `boldOn()`/`boldOff()`)

## Testing

Created comprehensive test that verifies:
- Large bold centered headers
- Normal centered subheaders  
- Left-aligned order details
- Right-aligned totals
- Centered QR codes and footers

## Expected Output

The printed receipt should now match the third image provided, with:
- **"Mythri Cinemas"** - Large, bold, centered
- **Address lines** - Normal size, centered
- **Order details** - Left-aligned
- **Total** - Right-aligned, bold
- **QR code** - Centered
- **Footer messages** - Centered

## Files Modified

- `src/printer_manager.py` - Enhanced NamedPrinterWrapper with ESC/POS commands
- `.gitignore` - Comprehensive Python gitignore patterns
- Added persistent formatting state management
- Added ESP32-compatible format application

## Verification

Run the printer client and verify that:
1. Headers are properly sized and centered
2. Text alignment works correctly
3. Bold formatting is applied
4. QR codes are centered
5. Git no longer tracks cache/log files