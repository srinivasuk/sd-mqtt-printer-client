# SD MQTT Printer Mac - USB Thermal Printer Client

A Python port of the ESP32 firmware for Mac systems with USB thermal printers. This client maintains 100% compatibility with the existing server infrastructure while adapting to USB printer hardware.

## 🚀 Features

- **100% MQTT Protocol Compatibility**: Uses the same topic structure and message formats as ESP32 firmware
- **USB Thermal Printer Support**: Works with ESC/POS compatible USB thermal printers
- **QR Code Generation**: Supports both bitmap and URL-based QR codes with multiple sizes
- **Printer Status Monitoring**: Real-time paper, cover, and error detection
- **Heartbeat System**: Regular status updates to server (configurable interval)
- **Error Recovery**: Automatic reconnection and error handling
- **Template Support**: Handles all print template formats from server
- **Variable Replacement**: Full support for dynamic content in receipts
- **Logging**: Comprehensive logging with file rotation and colored console output

## 📋 Requirements

- **macOS**: 10.14 or later
- **Python**: 3.9 or later
- **USB Thermal Printer**: ESC/POS compatible (80mm recommended)
- **Poetry**: For dependency management

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd sd-mqtt-printer-mac
   ```

2. **Install Poetry** (if not already installed):
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

3. **Install dependencies**:
   ```bash
   poetry install
   ```

4. **Configure environment**:
   ```bash
   cp env.example .env
   # Edit .env with your settings
   ```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with your configuration:

```env
# MQTT Configuration
MQTT_BROKER=printer.scandeer.com
MQTT_PORT=1883
MQTT_USERNAME=your_username
MQTT_PASSWORD=your_password

# Printer Configuration
PRINTER_NAME=your_printer_name
PRINTER_VENDOR_ID=0x04b8
PRINTER_PRODUCT_ID=0x0202

# System Configuration
MAC_ADDRESS=auto
HEARTBEAT_INTERVAL=30
DEBUG_MODE=true

# QR Code Configuration
QR_ERROR_CORRECTION=M
QR_BORDER=4
QR_BOX_SIZE=10

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=printer_client.log
LOG_MAX_SIZE=10MB
LOG_BACKUP_COUNT=5
```

### Printer Setup

1. **Connect your USB thermal printer**
2. **Find your printer name**:
   ```bash
   lpstat -p
   ```
3. **Update PRINTER_NAME** in `.env` with the correct name
4. **For direct USB connection**, find vendor/product IDs:
   ```bash
   system_profiler SPUSBDataType | grep -A 5 -B 5 "Thermal\|Receipt\|POS"
   ```

## 🚦 Usage

### Start the Client

```bash
poetry run python main.py
```

### Run as Service (macOS)

Create a launchd service file:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.scandeer.mqtt-printer</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/poetry</string>
        <string>run</string>
        <string>python</string>
        <string>main.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/path/to/sd-mqtt-printer-mac</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

### Test the Printer

```bash
poetry run python -c "from printer_manager import printer_manager; printer_manager.connect(); printer_manager.test_print()"
```

## 📡 MQTT Topics

The client uses the same topic structure as the ESP32 firmware:

- **Print Commands**: `{username}/pt/{printer_id}/p`
- **Status Updates**: `{username}/pt/{printer_id}/a`
- **Heartbeat**: `{username}/pt/{printer_id}/h`
- **Error Reports**: `{username}/pt/{printer_id}/e`
- **Recovery**: `{username}/pt/{printer_id}/r`

## 🖨️ Supported Print Elements

### Text Elements
- Plain text with variable replacement
- Formatted text (bold, size, alignment)
- Empty lines for spacing

### Formatting Commands
```json
{"f": {"a": "c", "b": true, "s": 2}}
```
- `a`: Alignment (l/c/r)
- `b`: Bold (true/false)
- `s`: Size (0=small, 1=normal, 2=large)

### Line Elements
```json
{"line": "solid"}
{"line": {"type": "dotted", "width": 48}}
```

### QR Code Elements
```json
{"qr_url": "https://example.com", "qr_size": 10, "qr_alignment": "center"}
{"qr_bitmap": {"width": 128, "height": 128, "data": [...]}}
```

## 🔧 Template Variables

Supports all standard template variables:

- `{{business_name}}`
- `{{business_address}}`
- `{{business_street}}`
- `{{business_city}}`
- `{{business_state}}`
- `{{business_country}}`
- `{{business_postal_code}}`
- `{{business_phone}}`
- `{{order_id}}`
- `{{customer_name}}`
- `{{customer_phone}}`
- `{{total_amount}}`
- `{{order_time}}`
- `{{selected_screen}}`
- `{{show_time}}`
- `{{seat_number}}`

## 📊 Status Monitoring

The client provides comprehensive status monitoring:

### Printer Status
- Connection status
- Paper levels
- Cover status
- Error conditions
- Print statistics

### MQTT Status
- Connection status
- Message counts
- Reconnection attempts
- Topic subscriptions

### System Status
- Memory usage
- Uptime
- Recovery attempts
- Configuration details

## 🔍 Troubleshooting

### Common Issues

1. **Printer Not Found**:
   - Check USB connection
   - Verify printer name with `lpstat -p`
   - Try different vendor/product IDs

2. **MQTT Connection Failed**:
   - Verify broker address and port
   - Check username/password
   - Ensure network connectivity

3. **Print Quality Issues**:
   - Check paper type and quality
   - Verify printer settings
   - Test with different content

4. **QR Codes Not Printing**:
   - Ensure printer supports graphics
   - Try different QR sizes
   - Check QR content length

### Debug Mode

Enable debug mode in `.env`:
```env
DEBUG_MODE=true
LOG_LEVEL=DEBUG
```

This provides detailed logging of all operations.

### Log Files

Logs are written to `printer_client.log` with automatic rotation:
- File size limit: 10MB (configurable)
- Backup count: 5 files (configurable)
- Colored console output for easy reading

## 🏗️ Architecture

### Core Components

1. **Config Module**: Environment configuration management
2. **Logger Module**: Structured logging with colors and rotation
3. **Printer Manager**: USB printer communication and status
4. **MQTT Client**: Server communication and message handling
5. **QR Generator**: QR code creation and bitmap processing
6. **Formatting Utils**: Text processing and template variables
7. **Bitmap Utils**: Image processing for QR codes

### Data Flow

1. **Startup**: Connect to printer and MQTT broker
2. **Heartbeat**: Regular status updates to server
3. **Print Request**: Receive MQTT message with print data
4. **Processing**: Parse elements, replace variables, format content
5. **Printing**: Send ESC/POS commands to USB printer
6. **Status**: Report print completion back to server

## 🤝 Compatibility

### ESP32 Firmware Compatibility

This client maintains 100% compatibility with the original ESP32 firmware:

- Same MQTT topic structure
- Same message formats
- Same print element types
- Same variable replacement
- Same status reporting
- Same error handling

### Server Compatibility

Works with existing server infrastructure without modifications:

- Same printer configuration
- Same template system
- Same business logic
- Same monitoring dashboard

## 📝 Development

### Project Structure

```
sd-mqtt-printer-mac/
├── config.py              # Configuration management
├── main.py                # Main application
├── mqtt_client.py         # MQTT communication
├── printer_manager.py     # USB printer interface
├── qr_generator.py        # QR code generation
├── utils/
│   ├── __init__.py
│   ├── logger.py          # Logging utilities
│   ├── formatting.py      # Text formatting
│   └── bitmap.py          # Bitmap processing
├── pyproject.toml         # Poetry configuration
├── README.md              # This file
└── .env                   # Environment variables
```

### Adding New Features

1. **New Print Elements**: Add parsing in `utils/formatting.py`
2. **New Status Fields**: Update `printer_manager.py`
3. **New MQTT Topics**: Add handlers in `mqtt_client.py`
4. **New Configuration**: Update `config.py`

### Testing

```bash
# Run printer test
poetry run python -c "from printer_manager import printer_manager; printer_manager.connect(); printer_manager.test_print()"

# Test QR generation
poetry run python -c "from qr_generator import qr_generator; print(qr_generator.create_test_qr())"

# Test MQTT connection
poetry run python -c "from mqtt_client import mqtt_client; print(mqtt_client.connect())"
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Original ESP32 firmware developers
- Python-escpos library maintainers
- Paho MQTT Python client developers
- QRCode library contributors 
