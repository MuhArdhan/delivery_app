<template>
  <div class="relative w-full h-full min-h-[420px] bg-slate-900 rounded-lg overflow-hidden border border-slate-700 shadow-inner">
    <div ref="mapContainer" class="w-full h-full z-0"></div>

    <!-- Map Overlay Stats / Filter -->
    <div class="absolute top-3 right-3 z-10 bg-slate-900/90 backdrop-blur-md px-3 py-1.5 rounded-md border border-slate-700 text-xs text-slate-200 shadow-md flex items-center space-x-3">
      <span class="flex items-center space-x-1.5">
        <span class="w-2.5 h-2.5 rounded bg-indigo-500"></span>
        <span>Asal</span>
      </span>
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

    <!-- Route Polyline Status Banner -->
    <div
      v-if="routeInfo && routeInfo.route_points && routeInfo.route_points.length > 0"
      class="absolute bottom-3 left-3 z-10 bg-slate-900/90 backdrop-blur-md px-3 py-1.5 rounded-md border border-slate-700 text-xs text-slate-200 shadow-md flex items-center space-x-2"
    >
      <span class="w-2 h-2 rounded-full bg-sky-400"></span>
      <span class="font-medium">Rute Rencana:</span>
      <span class="text-slate-300">{{ routeInfo.distance_km || 0 }} km (Est. {{ routeInfo.duration_min || 0 }} mnt)</span>
    </div>

    <!-- Routing Unavailable Warning & Retry -->
    <div
      v-else-if="routeInfo && routeInfo.success === false"
      class="absolute bottom-3 left-3 z-10 bg-amber-950/90 backdrop-blur-md px-3 py-1.5 rounded-md border border-amber-800 text-xs text-amber-200 shadow-md flex items-center space-x-2"
    >
      <span>{{ routeInfo.message || 'Rute jalan belum tersedia' }}</span>
      <button
        type="button"
        @click="$emit('retry-route')"
        class="px-2 py-0.5 bg-amber-800 hover:bg-amber-700 rounded text-[11px] text-white font-medium transition"
      >
        Coba Lagi
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, onBeforeUnmount } from 'vue'
import L from 'leaflet'
import { trackingMethodLabel } from '@/utils/tracking'

const props = defineProps({
  markers: {
    type: Array,
    default: () => []
  },
  routePolyline: {
    type: Array,
    default: () => []
  },
  routeInfo: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['select-marker', 'retry-route'])

const mapContainer = ref(null)
let map = null
let markerLayer = null
let polylineLayer = null

function getMarkerColor(status, type) {
  if (type === 'origin') return '#6366f1' // indigo-500
  if (status === 'Delivered' || status === 'Terkirim') return '#10b981' // emerald-500
  if (status === 'In Transit' || status === 'Dalam Pengiriman') return '#3b82f6' // blue-500
  return '#f59e0b' // amber-500
}

function createCustomIcon(marker) {
  if (marker.type === 'origin') {
    const iconHtml = `
      <div style="position: relative; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center;">
        <div style="width: 22px; height: 22px; border-radius: 6px; background: #4f46e5; border: 2px solid #ffffff; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.4); display: flex; align-items: center; justify-content: center; color: white; font-size: 10px; font-weight: 700;">
          A
        </div>
      </div>
    `
    return L.divIcon({
      html: iconHtml,
      className: 'custom-fleet-origin-pin',
      iconSize: [30, 30],
      iconAnchor: [15, 15],
      popupAnchor: [0, -15]
    })
  }

  const color = getMarkerColor(marker.status, marker.type)
  const isVisited = marker.visited || marker.status === 'Delivered' || marker.status === 'Terkirim'
  const stopNumber = marker.stop_number || marker.idx || ''

  const iconHtml = `
    <div style="position: relative; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center;">
      ${!isVisited ? `<div style="position: absolute; width: 100%; height: 100%; border-radius: 50%; background: ${color}; opacity: 0.25; animation: ping 2s cubic-bezier(0, 0, 0.2, 1) infinite;"></div>` : ''}
      <div style="width: 20px; height: 20px; border-radius: 50%; background: ${color}; border: 2px solid #ffffff; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.35); display: flex; align-items: center; justify-content: center; color: white; font-size: 10px; font-weight: 700;">
        ${stopNumber ? `<span>${stopNumber}</span>` : `<span style="width: 5px; height: 5px; border-radius: 50%; background: #ffffff;"></span>`}
      </div>
    </div>
  `

  return L.divIcon({
    html: iconHtml,
    className: 'custom-fleet-pin',
    iconSize: [30, 30],
    iconAnchor: [15, 15],
    popupAnchor: [0, -15]
  })
}

function renderMarkersAndRoute() {
  if (!map) return

  // 1. Render Markers
  if (markerLayer) {
    markerLayer.clearLayers()
  } else {
    markerLayer = L.layerGroup().addTo(map)
  }

  const bounds = []

  props.markers.forEach((m) => {
    if (m.lat === null || m.lat === undefined || m.lng === null || m.lng === undefined) return
    const numLat = Number(m.lat)
    const numLng = Number(m.lng)
    if (isNaN(numLat) || isNaN(numLng)) return
    if (numLat === 0 && numLng === 0) return

    const latLng = [numLat, numLng]
    bounds.push(latLng)

    const icon = createCustomIcon(m)
    const marker = L.marker(latLng, { icon })

    const confirmationInfo = m.confirmed_at_text ? `<div style="color: #059669; font-size: 10px; font-weight: 600; margin-bottom: 4px;">${m.confirmed_at_text}</div>` : ''

    const popupHtml = `
      <div style="font-family: inherit; font-size: 12px; color: #1e293b; min-width: 190px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
          <strong style="color: #0f172a; font-size: 13px;">${m.id}</strong>
          <span style="font-size: 10px; font-weight: 600; padding: 2px 6px; border-radius: 4px; background: ${getMarkerColor(m.status, m.type)}20; color: ${getMarkerColor(m.status, m.type)};">
            ${m.status}
          </span>
        </div>
        ${confirmationInfo}
        <div style="font-weight: 600; color: #334155; margin-bottom: 3px;">${m.customer || 'Pelanggan'}</div>
        <div style="color: #64748b; font-size: 11px; line-height: 1.3; margin-bottom: 8px;">${m.address || '-'}</div>
        <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #f1f5f9; padding-top: 6px;">
          <span style="font-size: 10px; color: #64748b;">${trackingMethodLabel(m.method)}</span>
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

  // 2. Render Polyline (Road Route)
  if (polylineLayer) {
    polylineLayer.clearLayers()
  } else {
    polylineLayer = L.layerGroup().addTo(map)
  }

  const polyCoords = props.routePolyline || []
  if (polyCoords.length > 1) {
    const polyline = L.polyline(polyCoords, {
      color: '#0284c7',
      weight: 4,
      opacity: 0.85,
      lineJoin: 'round'
    })

    const routeDistance = props.routeInfo?.distance_km ? `${props.routeInfo.distance_km} km` : ''
    polyline.bindTooltip(`Rute Rencana ${routeDistance}`, { sticky: true })
    polylineLayer.addLayer(polyline)

    // Add polyline points to bounds
    polyCoords.forEach(p => bounds.push(p))
  }

  // 3. Fit Bounds
  if (bounds.length > 0) {
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 })
  }
}

function resetView() {
  if (!map) return
  const valid = (props.markers || []).filter(m => m.lat != null && m.lng != null && (Number(m.lat) !== 0 || Number(m.lng) !== 0))
  const bounds = valid.map(m => [Number(m.lat), Number(m.lng)])

  if (props.routePolyline && props.routePolyline.length > 0) {
    props.routePolyline.forEach(p => bounds.push(p))
  }

  if (bounds.length > 0) {
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 })
    return
  }

  map.setView([-7.6147, 110.6869], 10)
}

onMounted(() => {
  if (!mapContainer.value) return

  map = L.map(mapContainer.value, {
    zoomControl: false,
    attributionControl: true
  }).setView([-7.6147, 110.6869], 10)

  L.control.zoom({ position: 'bottomright' }).addTo(map)

  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(map)

  renderMarkersAndRoute()
})

watch(() => [props.markers, props.routePolyline], () => {
  renderMarkersAndRoute()
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
    transform: scale(2.2);
    opacity: 0;
  }
}

.custom-fleet-pin, .custom-fleet-origin-pin {
  background: transparent;
  border: none;
}
</style>
