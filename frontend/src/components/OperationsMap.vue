<template>
  <div class="relative w-full h-full min-h-[420px] bg-slate-900 rounded-lg overflow-hidden border border-slate-700 shadow-inner">
    <div ref="mapContainer" class="w-full h-full z-0"></div>

    <!-- Map Overlay Stats / Filter -->
    <div class="absolute top-3 right-3 z-10 bg-slate-900/90 backdrop-blur-md px-3 py-1.5 rounded-md border border-slate-700 text-xs text-slate-200 shadow-md flex items-center space-x-3">
      <span class="flex items-center space-x-1.5">
        <span class="w-2 h-2 rounded-full bg-amber-400"></span>
        <span>Siap Kirim</span>
      </span>
      <span class="flex items-center space-x-1.5">
        <span class="w-2 h-2 rounded-full bg-blue-500"></span>
        <span>Dalam Pengiriman</span>
      </span>
      <span class="flex items-center space-x-1.5">
        <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
        <span>Terkirim</span>
      </span>
      <button 
        @click="resetView" 
        class="ml-2 px-2 py-0.5 bg-slate-800 hover:bg-slate-700 rounded text-slate-300 text-[11px] font-medium transition"
        title="Pusatkan Peta"
      >
        Reset
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, onBeforeUnmount } from 'vue'
import L from 'leaflet'

const props = defineProps({
  markers: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['select-marker'])

const mapContainer = ref(null)
let map = null
let markerLayer = null

function getMarkerColor(status) {
  if (status === 'Delivered') return '#10b981' // emerald-500
  if (status === 'In Transit') return '#3b82f6' // blue-500
  return '#f59e0b' // amber-500
}

function createCustomIcon(marker) {
  const color = getMarkerColor(marker.status)
  
  const iconHtml = `
    <div style="position: relative; width: 28px; height: 28px; display: flex; align-items: center; justify-content: center;">
      <div style="position: absolute; width: 100%; height: 100%; border-radius: 50%; background: ${color}; opacity: 0.2; animation: ping 2s cubic-bezier(0, 0, 0.2, 1) infinite;"></div>
      <div style="width: 18px; height: 18px; border-radius: 50%; background: ${color}; border: 2px solid #ffffff; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3); display: flex; align-items: center; justify-content: center;">
        <span style="width: 5px; height: 5px; border-radius: 50%; background: #ffffff;"></span>
      </div>
    </div>
  `

  return L.divIcon({
    html: iconHtml,
    className: 'custom-fleet-pin',
    iconSize: [28, 28],
    iconAnchor: [14, 14],
    popupAnchor: [0, -14]
  })
}

function renderMarkers() {
  if (!map) return
  if (markerLayer) {
    markerLayer.clearLayers()
  } else {
    markerLayer = L.layerGroup().addTo(map)
  }

  const bounds = []

  props.markers.forEach((m) => {
    if (!m.lat || !m.lng) return
    const latLng = [Number(m.lat), Number(m.lng)]
    bounds.push(latLng)

    const icon = createCustomIcon(m)
    const marker = L.marker(latLng, { icon })

    const popupHtml = `
      <div style="font-family: inherit; font-size: 12px; color: #1e293b; min-width: 190px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
          <strong style="color: #0f172a; font-size: 13px;">${m.id}</strong>
          <span style="font-size: 10px; font-weight: 600; padding: 2px 6px; border-radius: 4px; background: ${getMarkerColor(m.status)}20; color: ${getMarkerColor(m.status)};">
            ${m.status}
          </span>
        </div>
        <div style="font-weight: 600; color: #334155; margin-bottom: 3px;">${m.customer || 'Pelanggan'}</div>
        <div style="color: #64748b; font-size: 11px; line-height: 1.3; margin-bottom: 8px;">${m.address || '-'}</div>
        <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #f1f5f9; padding-top: 6px;">
          <span style="font-size: 10px; color: #64748b;">${m.method}</span>
          <button id="btn-popup-${m.id}" style="background: #0284c7; color: white; border: none; border-radius: 4px; padding: 3px 8px; font-size: 11px; cursor: pointer;">
            Detail
          </button>
        </div>
      </div>
    `

    marker.bindPopup(popupHtml)
    marker.on('popupopen', () => {
      const btn = document.getElementById(`btn-popup-${m.id}`)
      if (btn) {
        btn.onclick = () => emit('select-marker', m)
      }
    })

    markerLayer.addLayer(marker)
  })

  if (bounds.length > 0) {
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 })
  }
}

function resetView() {
  if (!map) return
  if (props.markers && props.markers.length > 0) {
    const bounds = props.markers.filter(m => m.lat && m.lng).map(m => [Number(m.lat), Number(m.lng)])
    if (bounds.length) {
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 })
      return
    }
  }
  map.setView([-6.2000, 106.8166], 11)
}

onMounted(() => {
  if (!mapContainer.value) return

  map = L.map(mapContainer.value, {
    zoomControl: false,
    attributionControl: true
  }).setView([-6.2000, 106.8166], 11)

  L.control.zoom({ position: 'bottomright' }).addTo(map)

  // Public OSM tiles: no bulk downloads or offline prefetching.
  // Usage policy: https://operations.osmfoundation.org/policies/tiles/
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(map)

  renderMarkers()
})

watch(() => props.markers, () => {
  renderMarkers()
}, { deep: true })

onBeforeUnmount(() => {
  if (map) {
    map.remove()
    map = null
  }
})
</script>

<style>
@keyframes ping {
  75%, 100% {
    transform: scale(2);
    opacity: 0;
  }
}
.custom-fleet-pin {
  background: transparent !important;
  border: none !important;
}
</style>
