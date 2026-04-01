import React, { useState, useEffect, useRef } from 'react';
import * as THREE from 'three';
import { basePath, isStaticMode, getApiUrl } from '../config';

interface ThreePanoramaViewerProps {
  panoId: string | null;
  treeLat?: number;
  treeLng?: number;
  clickedImagePath?: string;
}

interface MaskPolygon {
  pts: [number, number][];
  ip: string; // image_path
}

interface PrecomputedMaskData {
  polygons: MaskPolygon[];
}

/**
 * Fetch pre-computed mask polygons for a panorama.
 * Returns null if mask data is not available.
 */
async function fetchMaskData(panoId: string): Promise<PrecomputedMaskData | null> {
  try {
    // On GH Pages, fetch from static files; on Render, could use API
    const url = isStaticMode
      ? `${basePath}data/masks/${panoId}.json`
      : `${getApiUrl()}/api/mask-data/${panoId}`;

    const response = await fetch(url);
    if (!response.ok) return null;

    const data = await response.json();
    // Static mode returns pre-computed format; API returns raw format
    if (data.polygons) return data as PrecomputedMaskData;
    return null;
  } catch {
    return null;
  }
}

/**
 * Draw mask polygon overlays on the panorama canvas.
 */
function drawMasks(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
  masks: PrecomputedMaskData,
  clickedImagePath?: string
) {
  for (const mask of masks.polygons) {
    if (mask.pts.length < 3) continue;

    const isHighlight = !!(clickedImagePath && mask.ip === clickedImagePath);

    // Convert normalized 0-1 coordinates to pixel coordinates
    const pixelPts = mask.pts.map(([nx, ny]) => [nx * width, ny * height] as [number, number]);

    // Draw filled polygon with low opacity
    ctx.beginPath();
    ctx.moveTo(pixelPts[0][0], pixelPts[0][1]);
    for (let i = 1; i < pixelPts.length; i++) {
      ctx.lineTo(pixelPts[i][0], pixelPts[i][1]);
    }
    ctx.closePath();

    ctx.fillStyle = isHighlight ? 'rgba(0, 255, 0, 0.08)' : 'rgba(0, 255, 0, 0.05)';
    ctx.fill();

    // Draw outline
    ctx.strokeStyle = isHighlight ? 'rgba(0, 255, 0, 0.9)' : 'rgba(0, 255, 0, 0.7)';
    ctx.lineWidth = isHighlight ? 3 : 2;
    ctx.stroke();

    if (isHighlight) {
      // Draw bounding box
      const xs = pixelPts.map(p => p[0]);
      const ys = pixelPts.map(p => p[1]);
      const x1 = Math.min(...xs), x2 = Math.max(...xs);
      const y1 = Math.min(...ys), y2 = Math.max(...ys);

      ctx.strokeStyle = 'rgba(255, 0, 0, 0.9)';
      ctx.lineWidth = 4;
      ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

      // Draw center point
      const cx = (x1 + x2) / 2, cy = (y1 + y2) / 2;
      ctx.beginPath();
      ctx.arc(cx, cy, 12, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(255, 0, 0, 0.9)';
      ctx.fill();
      ctx.strokeStyle = 'white';
      ctx.lineWidth = 3;
      ctx.stroke();
    }
  }
}

/**
 * Fetch panorama tiles directly from Google's tile server and stitch them
 * into a single equirectangular panorama image on a canvas,
 * then overlay mask annotations.
 */
async function fetchPanoramaTiles(panoId: string, clickedImagePath?: string): Promise<string> {
  const zoom = 2;
  const tilesX = 2 ** zoom; // 4
  const tilesY = 2 ** (zoom - 1); // 2
  const tileSize = 512;
  const width = tilesX * tileSize;
  const height = tilesY * tileSize;

  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d')!;

  // Fetch tiles and mask data concurrently
  const maskPromise = fetchMaskData(panoId);

  const tilePromises: Promise<{ x: number; y: number; img: HTMLImageElement | null }>[] = [];
  for (let y = 0; y < tilesY; y++) {
    for (let x = 0; x < tilesX; x++) {
      const url = `https://cbk0.google.com/cbk?output=tile&panoid=${panoId}&zoom=${zoom}&x=${x}&y=${y}`;
      tilePromises.push(
        new Promise((resolve) => {
          const img = new Image();
          img.crossOrigin = 'anonymous';
          img.onload = () => resolve({ x, y, img });
          img.onerror = () => resolve({ x, y, img: null });
          img.src = url;
        })
      );
    }
  }

  const [tiles, maskData] = await Promise.all([Promise.all(tilePromises), maskPromise]);
  let validTiles = 0;

  for (const tile of tiles) {
    if (tile.img) {
      ctx.drawImage(tile.img, tile.x * tileSize, tile.y * tileSize);
      validTiles++;
    }
  }

  if (validTiles === 0) {
    throw new Error('This panorama is no longer available on Google Street View');
  }

  // Draw mask overlays on top of the panorama
  if (maskData && maskData.polygons.length > 0) {
    drawMasks(ctx, width, height, maskData, clickedImagePath);
    console.log(`🎭 Drew ${maskData.polygons.length} mask overlays on panorama`);
  }

  return canvas.toDataURL('image/jpeg', 0.92);
}

export const ThreePanoramaViewer: React.FC<ThreePanoramaViewerProps> = ({ 
  panoId, 
  treeLat, 
  treeLng,
  clickedImagePath
}) => {
  const [panoramaImage, setPanoramaImage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mountRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<{
    scene: THREE.Scene;
    camera: THREE.PerspectiveCamera;
    renderer: THREE.WebGLRenderer;
    sphere: THREE.Mesh;
    isMouseDown: boolean;
    mouseX: number;
    mouseY: number;
    lon: number;
    lat: number;
    phi: number;
    theta: number;
    animate: () => void;
    cleanup: () => void;
  } | null>(null);

  useEffect(() => {
    if (!panoId) {
      setPanoramaImage(null);
      setError(null);
      return;
    }

    const fetchPanorama = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Fetch panorama tiles directly from Google's tile server
        // and overlay mask annotations
        const imageDataUrl = await fetchPanoramaTiles(panoId, clickedImagePath);
        setPanoramaImage(imageDataUrl);
        
      } catch (err) {
        console.error('Error fetching panorama:', err);
        setError(err instanceof Error ? err.message : 'Failed to load panorama');
      } finally {
        setLoading(false);
      }
    };

    fetchPanorama();
  }, [panoId, clickedImagePath]);

  // Initialize Three.js scene when panorama loads
  useEffect(() => {
    if (!panoramaImage || !mountRef.current) return;

    const mount = mountRef.current;
    
    // Scene setup
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, mount.clientWidth / mount.clientHeight, 1, 1100);
    const renderer = new THREE.WebGLRenderer({ antialias: true });

    // Improve clarity and correct color space
    renderer.setPixelRatio(window.devicePixelRatio || 1);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.NoToneMapping;
    renderer.toneMappingExposure = 1.0;
    renderer.setSize(mount.clientWidth, mount.clientHeight);
    mount.appendChild(renderer.domElement);

    // Create sphere geometry for panorama with high resolution
    const geometry = new THREE.SphereGeometry(500, 128, 64);
    // Flip the geometry inside out
    geometry.scale(-1, 1, 1);

    // Load texture with high quality settings
    const textureLoader = new THREE.TextureLoader();
    const texture = textureLoader.load(panoramaImage, () => {
      // Apply high quality sampling once the texture is loaded
      texture.colorSpace = THREE.SRGBColorSpace;
      texture.generateMipmaps = true;
      texture.minFilter = THREE.LinearMipmapLinearFilter;
      texture.magFilter = THREE.LinearFilter;
      texture.anisotropy = renderer.capabilities.getMaxAnisotropy();
      texture.needsUpdate = true;
    });
    
    const material = new THREE.MeshBasicMaterial({ map: texture });
    
    const sphere = new THREE.Mesh(geometry, material);
    scene.add(sphere);

    // Camera controls
    let isMouseDown = false;
    let mouseX = 0;
    let mouseY = 0;
    let lon = 0;
    let lat = 0;
    let phi = 0;
    let theta = 0;

    const onMouseDown = (event: MouseEvent) => {
      event.preventDefault();
      isMouseDown = true;
      mouseX = event.clientX;
      mouseY = event.clientY;
    };

    const onMouseUp = () => {
      isMouseDown = false;
    };

    const onMouseMove = (event: MouseEvent) => {
      if (!isMouseDown) return;

      const deltaX = event.clientX - mouseX;
      const deltaY = event.clientY - mouseY;

      mouseX = event.clientX;
      mouseY = event.clientY;

      lon -= deltaX * 0.1;
      lat += deltaY * 0.1;
      lat = Math.max(-85, Math.min(85, lat));
    };

    const onWheel = (event: WheelEvent) => {
      event.preventDefault();
      const fov = camera.fov + event.deltaY * 0.05;
      camera.fov = THREE.MathUtils.clamp(fov, 10, 75);
      camera.updateProjectionMatrix();
    };

    const animate = () => {
      phi = THREE.MathUtils.degToRad(90 - lat);
      theta = THREE.MathUtils.degToRad(lon);

      const x = 500 * Math.sin(phi) * Math.cos(theta);
      const y = 500 * Math.cos(phi);
      const z = 500 * Math.sin(phi) * Math.sin(theta);

      camera.lookAt(x, y, z);
      renderer.render(scene, camera);
      requestAnimationFrame(animate);
    };

    // Event listeners
    mount.addEventListener('mousedown', onMouseDown);
    mount.addEventListener('mousemove', onMouseMove);
    mount.addEventListener('mouseup', onMouseUp);
    mount.addEventListener('wheel', onWheel);
    mount.addEventListener('contextmenu', (e) => e.preventDefault());

    // Handle resize
    const handleResize = () => {
      camera.aspect = mount.clientWidth / mount.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(mount.clientWidth, mount.clientHeight);
    };
    window.addEventListener('resize', handleResize);

    // Start animation
    animate();

    // Store references for cleanup
    sceneRef.current = {
      scene,
      camera,
      renderer,
      sphere,
      isMouseDown,
      mouseX,
      mouseY,
      lon,
      lat,
      phi,
      theta,
      animate,
      cleanup: () => {
        mount.removeEventListener('mousedown', onMouseDown);
        mount.removeEventListener('mousemove', onMouseMove);
        mount.removeEventListener('mouseup', onMouseUp);
        mount.removeEventListener('wheel', onWheel);
        window.removeEventListener('resize', handleResize);
        
        if (mount.contains(renderer.domElement)) {
          mount.removeChild(renderer.domElement);
        }
        
        geometry.dispose();
        material.dispose();
        texture.dispose();
        
        // Clean up any additional meshes (if any)
        scene.children.forEach(child => {
          if (child instanceof THREE.Mesh && child !== sphere) {
            child.geometry.dispose();
            if (child.material instanceof THREE.Material) {
              child.material.dispose();
            }
          }
        });
        
        renderer.dispose();
      }
    };

    // Cleanup on unmount
    return () => {
      if (sceneRef.current) {
        sceneRef.current.cleanup();
      }
    };
  }, [panoramaImage]);

  return (
    <div style={{
      width: '100%',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      backgroundColor: '#f5f5f5',
      border: '1px solid #ddd',
      borderRadius: '8px',
      overflow: 'hidden',
      position: 'relative'
    }}>
      {!panoId ? (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          textAlign: 'center',
          color: '#666',
          fontSize: '16px',
          padding: '20px'
        }}>
          <div>
            <h3>360° Panorama Viewer</h3>
            <p>Click on a tree to view its 360° panorama</p>
            <p style={{ fontSize: '12px', color: '#999' }}>
              🖱️ Drag to look around • 🔍 Scroll to zoom
            </p>
          </div>
        </div>
      ) : loading ? (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          textAlign: 'center',
          color: '#666',
          fontSize: '16px'
        }}>
          <div>
            <div style={{
              width: '40px',
              height: '40px',
              border: '4px solid #f3f3f3',
              borderTop: '4px solid #3498db',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite',
              margin: '0 auto 20px'
            }} />
            <p>Loading 360° panorama...</p>
          </div>
        </div>
      ) : error ? (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          textAlign: 'center',
          color: '#d32f2f',
          fontSize: '16px',
          padding: '20px'
        }}>
          <div>
            <h3>Error</h3>
            <p>{error}</p>
          </div>
        </div>
      ) : panoramaImage ? (
        <>
          {/* Header with panorama info */}
          <div style={{
            position: 'absolute',
            top: '10px',
            left: '10px',
            right: '10px',
            zIndex: 1000,
            backgroundColor: 'rgba(0, 0, 0, 0.7)',
            color: 'white',
            padding: '8px 12px',
            borderRadius: '4px',
            fontSize: '12px',
            pointerEvents: 'none'
          }}>
            <div><strong>Panorama ID:</strong> {panoId}</div>
            {treeLat && treeLng && (
              <div><strong>Tree Location:</strong> {treeLat.toFixed(6)}, {treeLng.toFixed(6)}</div>
            )}
            <div style={{ fontSize: '10px', marginTop: '4px', opacity: 0.8 }}>
              🖱️ Drag to look around • 🔍 Scroll to zoom • 🎭 Red overlays show detected trees
            </div>
          </div>

          {/* Three.js container */}
          <div 
            ref={mountRef} 
            style={{ 
              width: '100%', 
              height: '100%',
              cursor: 'grab'
            }}
          />
        </>
      ) : null}
      
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};
