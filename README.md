# Tree Map - React + deck.gl Implementation

This project combines **React + deck.gl** frontend with a **Python Flask API** backend for interactive tree mapping and street view visualization.

## 🚀 Features

- **Interactive map:** deck.gl-powered visualization with satellite imagery
- **Tree markers:** Forest green markers showing detected tree locations
- **Street view markers:** Blue markers showing street view panorama locations
- **3D panorama viewer:** Three.js-powered street view panorama display
- **Click interactions:** Click on any tree marker to view the street-level perspective
- **Layer controls:** Toggle visibility of different map layers

## 📁 Project Structure

```
src/
├── App.tsx                    # Main application component with deck.gl map
├── main.tsx                   # React entry point
├── types.ts                   # TypeScript type definitions
├── config.ts                  # Application configuration
├── utils/
│   └── dataLoader.ts          # CSV data loading and processing utilities
└── components/
    ├── ControlPanel.tsx       # Main control panel with layer and map controls
    ├── LayerControls.tsx      # Map layer visibility controls
    ├── BaseMapSwitcher.tsx    # Base map type switching component
    └── ThreePanoramaViewer.tsx # Three.js-powered panorama viewer

data/
└── south_delhi/               # Area-based data structure
    ├── trees.csv              # Tree detection data
    ├── panoramas.csv          # Street view panorama data
    └── masks/                 # Mask JSON files (79745 files)
        └── *_masks.json

public/
└── tree.svg                  # Tree icon for markers

Python Backend:
├── api_server.py             # Flask API server
├── mask_processor.py         # Image processing utilities
├── panorama_fetcher.py       # Street view panorama fetching
├── utils.py                  # General utilities
├── requirements.txt          # Python dependencies
└── start.sh                  # Automated startup script
```

## 🛠️ Installation & Setup

### 🚀 Quick Start (Recommended)

Use the automated startup script that handles everything:

```bash
./start.sh
```

This script will:

- ✅ Create Python virtual environment (`.venv`) if it doesn't exist
- ✅ Activate the virtual environment
- ✅ Install/verify Python dependencies from `requirements.txt`
- ✅ Install npm dependencies if needed
- ✅ Start the Python Flask API server on port 5001
- ✅ Start the React development server on port 3000
- ✅ Handle graceful shutdown with Ctrl+C

### Manual Setup (Alternative)

If you prefer manual setup or need to troubleshoot:

#### 1. Install Node.js Dependencies

```bash
npm install --legacy-peer-deps
```

> **Note:** The `--legacy-peer-deps` flag resolves dependency conflicts between deck.gl and luma.gl packages.

#### 2. Setup Python Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

#### 3. Start Servers

**Terminal 1 - Python API Server:**

```bash
source .venv/bin/activate
python api_server.py
```

**Terminal 2 - React Development Server:**

```bash
npm run dev
```

## 🎯 Usage

### Accessing the Application

After running `./start.sh`, the application will be available at:

- **Frontend**: http://localhost:3000
- **API**: http://localhost:5001

### Using the Interface

1. **Map Navigation:**

   - Pan and zoom to navigate the Delhi area
   - Use mouse wheel to zoom, click and drag to pan
   - Switch between satellite and street map views using the base map switcher
2. **Control Panel:**

   - Use the control panel on the top-right to toggle layer visibility
   - View counts for trees, street views, and connections
   - Switch between different base map types
3. **Tree Interaction:**

   - Click on any green tree marker to view its street-level perspective
   - The Three.js viewer will display the centered view of the tree from the street view panorama
   - Includes metadata like coordinates, confidence scores, and panorama ID
4. **Visual Elements:**

   - 🌳 **Green markers**: Detected trees
   - 🔵 **Blue markers**: Street view locations

### Stopping the Application

Press **Ctrl+C** in the terminal where `./start.sh` is running to gracefully stop both servers.

## 📊 Data

The application uses an area-based data structure located in the `data/` directory:

```
data/
└── south_delhi/               # Area-specific data folder
    ├── trees.csv              # Tree detection data with coordinates, confidence scores, and panorama references
    ├── panoramas.csv          # Street view panorama locations and metadata
    └── masks/                 # Mask JSON files for tree segmentation (79745 files)
```

This structure allows easy addition of new areas by creating new subfolders (e.g., `data/north_delhi/`) with the same file structure.

## 🛡️ API Integration

The React frontend communicates with the Python Flask API for:

- **Tree view generation**: `/api/tree-view/{csv_index}`
- **Tree information**: `/api/tree-info/{csv_index}`
- **Health checks**: `/health`

The API serves base64-encoded images of tree-centered views generated from street view panoramas.

## 🚀 Production Build

```bash
npm run build
```

This creates an optimized production build in the `dist/` directory.

To preview the production build:

```bash
npm run preview
```

## 🔧 Technical Stack

### Frontend

- **React 18** - Modern React with hooks and concurrent features
- **TypeScript** - Type-safe development
- **deck.gl** - High-performance WebGL-powered data visualization
- **Three.js** - 3D panorama viewer for street view visualization
- **Vite** - Fast build tool and development server
- **MapLibre GL** - Open-source mapping library
- **Papa Parse** - CSV parsing library
- **Axios** - HTTP client for API requests

### Backend

- **Python 3.13** - Backend runtime
- **Flask** - Web framework for API server
- **Flask-CORS** - Cross-origin resource sharing
- **OpenCV** - Computer vision and image processing
- **Pandas** - Data manipulation and analysis
- **NumPy** - Numerical computing
- **aiohttp** - Async HTTP client/server
- **streetlevel** - Street-level imagery processing

## 🐛 Troubleshooting

### Port Conflicts

- **Port 5000**: May be used by macOS ControlCenter (system process). Use port 5001 for the API instead.
- **Port 5001**: If occupied, kill existing processes with `lsof -ti:5001 | xargs kill -9`

### "Unable to connect to server" errors

- Make sure the Flask API server is running on port 5001
- Check that CORS is properly configured in `api_server.py`
- Verify the virtual environment is activated

### CSV loading errors

- Ensure CSV files are in the `data/south_delhi/` directory
- Check that file names match exactly: `trees.csv` and `panoramas.csv`
- Verify that the `masks/` folder exists in `data/south_delhi/`

### Dependency installation issues

- **Node.js**: Use `npm install --legacy-peer-deps` to resolve deck.gl peer dependency conflicts
- **Python**: Ensure you're using Python 3.13+ and have activated the virtual environment
- Clear npm cache with `npm cache clean --force` if needed

### Virtual Environment Issues

- If `.venv` is corrupted, delete it and run `./start.sh` again
- Make sure `python3` is available in your PATH
- On macOS, you may need to install Python via Homebrew: `brew install python`

## 📈 Performance

The React + deck.gl implementation offers significant performance improvements over the Python + pydeck version:

- **Faster rendering**: WebGL-accelerated rendering for thousands of markers
- **Better interactivity**: Smooth pan/zoom operations
- **Reduced memory usage**: More efficient data handling in the browser
- **Hot reloading**: Instant updates during development

## 📝 License

This project maintains the same license as the original Python implementation.
