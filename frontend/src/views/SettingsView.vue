<template>
  <div class="max-w-4xl space-y-6">
    <!-- Header -->
    <div class="bg-white rounded-xl p-5 border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-xs">
      <div>
        <h2 class="text-sm font-semibold text-slate-900 tracking-tight">Pengaturan Operasional & Layanan Rute</h2>
        <p class="text-xs text-slate-500">Konfigurasi rute, koordinat asal company, dan layanan tracking ekspedisi</p>
      </div>
    </div>

    <!-- 1. OSRM Routing Settings -->
    <div class="bg-white rounded-xl p-6 border border-slate-200 space-y-5 text-xs shadow-xs">
      <div class="flex items-center justify-between pb-3 border-b border-slate-100">
        <div class="flex items-center space-x-2.5">
          <div class="w-7 h-7 rounded-lg bg-sky-50 text-sky-600 flex items-center justify-center font-bold">
            <Route :size="15" />
          </div>
          <div>
            <span class="font-semibold text-slate-900 text-sm block">Open Source Routing Machine (OSRM)</span>
            <span class="text-slate-500 text-[11px]">Kalkulasi polyline rute jalan raya dan estimasi jarak pengiriman multi-drop</span>
          </div>
        </div>
        <label class="relative inline-flex items-center cursor-pointer">
          <input type="checkbox" v-model="form.osrm_enabled" class="sr-only peer" />
          <div class="w-10 h-5 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-sky-600"></div>
        </label>
      </div>

      <div class="space-y-3">
        <div>
          <label class="block font-semibold text-slate-700 uppercase tracking-wider text-[10px] mb-1.5">
            OSRM Base URL
          </label>
          <input
            v-model="form.osrm_base_url"
            type="text"
            placeholder="https://router.project-osrm.org atau http://localhost:5000"
            class="w-full px-3 py-2 rounded-lg border border-slate-200 focus:outline-none focus:border-slate-400 font-mono text-slate-800 text-xs"
          />
          <p class="text-[11px] text-slate-400 mt-1">
            Gunakan router publik OSM standar atau deploy instance Docker self-hosted lokal dengan file extract wilayah operasional (contoh: Jawa/Indonesia).
          </p>
        </div>
      </div>
    </div>

    <!-- 2. Company Dispatch Locations -->
    <div class="bg-white rounded-xl p-6 border border-slate-200 space-y-4 text-xs shadow-xs">
      <div class="flex items-center space-x-2.5 pb-3 border-b border-slate-100">
        <div class="w-7 h-7 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold">
          <MapPin :size="15" />
        </div>
        <div>
          <span class="font-semibold text-slate-900 text-sm block">Lokasi Asal Keberangkatan Company</span>
          <span class="text-slate-500 text-[11px]">Titik awal pengantaran untuk setiap Delivery Trip per entitas Company</span>
        </div>
      </div>

      <div class="space-y-3">
        <div
          v-for="c in companyList"
          :key="c.name"
          class="p-3.5 rounded-lg border border-slate-200 bg-slate-50/70 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
        >
          <div>
            <div class="flex items-center space-x-2">
              <span class="font-semibold text-slate-900 text-xs">{{ c.company_name || c.name }}</span>
              <span class="text-[10px] font-medium bg-slate-200/70 text-slate-700 px-1.5 py-0.5 rounded">{{ c.abbr }}</span>
            </div>
            <div class="text-[11px] text-slate-500 mt-0.5">
              <span v-if="c.has_dispatch_location" class="text-emerald-700 font-medium">
                Koordinat Terpasang: {{ c.dispatch_lat }}, {{ c.dispatch_lng }}
              </span>
              <span v-else class="text-amber-700 font-medium">
                Koordinat asal gudang belum diatur.
              </span>
            </div>
          </div>

          <button
            type="button"
            @click="openEditCompanyCoord(c)"
            class="px-3 py-1.5 rounded-lg border border-slate-300 hover:bg-slate-100 text-slate-700 text-xs font-medium transition"
          >
            {{ c.has_dispatch_location ? 'Ubah Koordinat' : 'Atur Koordinat' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 3. Biteship Ekspedisi Gateway -->
    <div class="bg-white rounded-xl p-6 border border-slate-200 space-y-6 text-xs shadow-xs">
      <div class="flex items-center justify-between pb-4 border-b border-slate-100">
        <div class="flex items-center space-x-2.5">
          <div class="w-7 h-7 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center font-bold">
            <Send :size="15" />
          </div>
          <div>
            <span class="font-semibold text-slate-900 text-sm block">Integrasi Gateway Ekspedisi (Biteship 3PL)</span>
            <span class="text-slate-500 text-[11px]">Cek tarif ongkir dan pelacakan resi otomatis pihak ketiga</span>
          </div>
        </div>
        <div class="flex items-center space-x-3">
          <button
            @click="testConnection"
            :disabled="testing"
            class="px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-medium transition flex items-center space-x-1"
          >
            <Zap :size="12" :class="testing ? 'animate-spin text-amber-600' : 'text-slate-500'" />
            <span>{{ testing ? 'Menguji...' : 'Uji Koneksi' }}</span>
          </button>
          <label class="relative inline-flex items-center cursor-pointer">
            <input type="checkbox" v-model="form.enabled" class="sr-only peer" />
            <div class="w-10 h-5 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-slate-900"></div>
          </label>
        </div>
      </div>

      <!-- Environment & API Key -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label class="block font-semibold text-slate-700 uppercase tracking-wider text-[10px] mb-1.5">
            Environment
          </label>
          <select
            v-model="form.environment"
            class="w-full px-3 py-2 rounded-lg border border-slate-200 focus:outline-none focus:border-slate-400 bg-white text-slate-700"
          >
            <option value="Sandbox">Sandbox (Testing / Mock)</option>
            <option value="Live">Live (Produksi Nyata)</option>
          </select>
        </div>

        <div>
          <label class="block font-semibold text-slate-700 uppercase tracking-wider text-[10px] mb-1.5">
            Biteship Secret API Key
          </label>
          <input
            v-model="form.api_key"
            type="password"
            placeholder="biteship_test.xxx / biteship_live.xxx"
            class="w-full px-3 py-2 rounded-lg border border-slate-200 focus:outline-none focus:border-slate-400 font-mono text-slate-800"
          />
        </div>
      </div>

      <!-- Auto Tracking & Sync Interval -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-4 border-t border-slate-100">
        <div>
          <label class="block font-semibold text-slate-700 uppercase tracking-wider text-[10px] mb-1.5">
            Auto-Tracking Resi Ekspedisi
          </label>
          <div class="flex items-center space-x-2 mt-2">
            <input type="checkbox" id="chk-auto" v-model="form.auto_tracking" class="rounded border-slate-300 text-slate-900 focus:ring-0 cursor-pointer" />
            <label for="chk-auto" class="text-slate-700 font-medium">Sinkronisasi status resi latar belakang otomatis</label>
          </div>
        </div>

        <div>
          <label class="block font-semibold text-slate-700 uppercase tracking-wider text-[10px] mb-1.5">
            Interval Pengecekan (Jam)
          </label>
          <input
            v-model.number="form.sync_interval_hours"
            type="number"
            min="1"
            max="24"
            class="w-full px-3 py-2 rounded-lg border border-slate-200 focus:outline-none focus:border-slate-400 text-slate-800"
          />
        </div>
      </div>

      <!-- Webhook Configuration -->
      <div class="pt-4 border-t border-slate-100">
        <label class="block font-semibold text-slate-700 uppercase tracking-wider text-[10px] mb-1.5">
          Webhook Endpoint (Biteship Dashboard)
        </label>
        <div class="flex items-center space-x-2">
          <input
            type="text"
            readonly
            :value="webhookUrl"
            class="flex-1 px-3 py-2 bg-slate-50 rounded-lg border border-slate-200 text-xs font-mono text-slate-600 select-all"
          />
          <button
            type="button"
            @click="copyWebhookUrl"
            class="px-3 py-2 border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-medium rounded-lg transition"
          >
            {{ copied ? 'Tersalin' : 'Salin URL' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Save Button -->
    <div class="flex justify-end pb-8">
      <button
        type="button"
        @click="saveSettings"
        :disabled="saving"
        class="px-5 py-2.5 bg-slate-900 hover:bg-slate-800 text-white font-medium rounded-lg transition flex items-center space-x-1.5 text-xs shadow-xs"
      >
        <Save :size="13" />
        <span>{{ saving ? 'Menyimpan...' : 'Simpan Seluruh Pengaturan' }}</span>
      </button>
    </div>

    <!-- Submodal: Edit Company Location -->
    <div v-if="isCompanyModalOpen" class="fixed inset-0 z-60 bg-slate-950/70 flex items-center justify-center p-4">
      <div class="bg-white rounded-xl shadow-xl max-w-md w-full border border-slate-200 overflow-hidden">
        <div class="bg-slate-900 text-white px-5 py-3.5 flex items-center justify-between border-b border-slate-800">
          <h4 class="font-semibold text-xs text-white">Atur Lokasi Keberangkatan Company</h4>
          <button @click="isCompanyModalOpen = false" class="text-slate-400 hover:text-white p-1">
            <X :size="14" />
          </button>
        </div>
        <div class="p-5 space-y-4 text-xs">
          <div>
            <span class="text-slate-400 block text-[11px]">Company:</span>
            <span class="font-semibold text-slate-800 text-sm">{{ activeCompany?.company_name || activeCompany?.name }}</span>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-[10px] font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Latitude *
              </label>
              <input
                v-model.number="companyCoordForm.lat"
                type="number"
                step="any"
                placeholder="-7.6147"
                class="w-full text-xs px-3 py-2 rounded-lg border border-slate-200 focus:outline-none focus:border-slate-400"
              />
            </div>
            <div>
              <label class="block text-[10px] font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Longitude *
              </label>
              <input
                v-model.number="companyCoordForm.lng"
                type="number"
                step="any"
                placeholder="110.6869"
                class="w-full text-xs px-3 py-2 rounded-lg border border-slate-200 focus:outline-none focus:border-slate-400"
              />
            </div>
          </div>
        </div>
        <div class="bg-slate-50 px-5 py-3 border-t border-slate-200 flex justify-end space-x-2">
          <button
            type="button"
            @click="isCompanyModalOpen = false"
            class="px-3 py-1.5 rounded-lg text-xs font-medium text-slate-600 hover:bg-slate-200 transition"
          >
            Batal
          </button>
          <button
            type="button"
            @click="saveCompanyLocation"
            :disabled="savingCompanyLocation || companyCoordForm.lat === null || companyCoordForm.lng === null"
            class="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-sky-600 hover:bg-sky-700 text-white transition disabled:opacity-50"
          >
            Simpan Lokasi
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { Zap, Save, Route, MapPin, Send, X } from 'lucide-vue-next'
import { DeliveryApi, callApi } from '@/api'

const saving = ref(false)
const testing = ref(false)
const copied = ref(false)
const webhookUrl = ref(window.location.origin + '/api/method/delivery_app.services.biteship.handle_webhook')

const companyList = ref([])
const isCompanyModalOpen = ref(false)
const activeCompany = ref(null)
const companyCoordForm = reactive({ lat: null, lng: null })
const savingCompanyLocation = ref(false)

const form = reactive({
  enabled: true,
  environment: 'Sandbox',
  api_key: '',
  webhook_secret: '',
  auto_tracking: true,
  sync_interval_hours: 3,
  supported_couriers: 'jne, jnt, sicepat, anteraja, ninja, pos, sentral, wahana, tiki, idexpress, lion, gosend, grab',
  osrm_enabled: true,
  osrm_base_url: 'https://router.project-osrm.org',
})

function copyWebhookUrl() {
  if (navigator?.clipboard?.writeText) {
    navigator.clipboard.writeText(webhookUrl.value)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  }
}

async function loadResources() {
  try {
    const fleet = await DeliveryApi.getFleetResources()
    companyList.value = fleet.companies || []
  } catch (err) {
    console.error('Failed to load fleet resources:', err)
  }
}

async function loadSettings() {
  try {
    const res = await DeliveryApi.getSettings()
    form.enabled = Boolean(res.enabled)
    form.environment = res.environment || 'Sandbox'
    form.api_key = res.has_api_key ? '********' : ''
    form.webhook_secret = res.has_webhook_secret ? '********' : ''
    form.auto_tracking = Boolean(res.auto_tracking)
    form.sync_interval_hours = res.sync_interval_hours || 3
    if (res.supported_couriers) form.supported_couriers = res.supported_couriers
    if (res.osrm_enabled !== undefined) form.osrm_enabled = Boolean(res.osrm_enabled)
    if (res.osrm_base_url) form.osrm_base_url = res.osrm_base_url
    if (res.webhook_endpoint) {
      webhookUrl.value = window.location.origin + res.webhook_endpoint
    }
  } catch (e) {
    console.error('Settings err:', e)
  }
}

async function saveSettings() {
  saving.value = true
  try {
    await DeliveryApi.saveSettings(form)
    alert('Pengaturan operasional dan routing berhasil disimpan.')
  } catch (err) {
    alert(err.message || 'Gagal menyimpan pengaturan')
  } finally {
    saving.value = false
  }
}

function openEditCompanyCoord(company) {
  activeCompany.value = company
  companyCoordForm.lat = company.dispatch_lat !== undefined ? company.dispatch_lat : null
  companyCoordForm.lng = company.dispatch_lng !== undefined ? company.dispatch_lng : null
  isCompanyModalOpen.value = true
}

async function saveCompanyLocation() {
  if (!activeCompany.value) return
  savingCompanyLocation.value = true
  try {
    const res = await DeliveryApi.setCompanyDispatchLocation(
      activeCompany.value.name,
      companyCoordForm.lat,
      companyCoordForm.lng
    )
    activeCompany.value.dispatch_lat = res.latitude
    activeCompany.value.dispatch_lng = res.longitude
    activeCompany.value.has_dispatch_location = res.has_location
    isCompanyModalOpen.value = false
  } catch (err) {
    alert(err.message || 'Gagal menyimpan lokasi company')
  } finally {
    savingCompanyLocation.value = false
  }
}

async function testConnection() {
  testing.value = true
  try {
    const res = await callApi('delivery_app.services.biteship.test_connection', {}, 'GET')
    if (res.success) {
      alert(`Koneksi Sukses! Terhubung ke Biteship API (${res.account_name}).`)
    } else {
      alert(`Koneksi Gagal: ${res.error}`)
    }
  } catch (err) {
    alert(`Error: ${err.message}`)
  } finally {
    testing.value = false
  }
}

onMounted(() => {
  loadSettings()
  loadResources()
})
</script>
