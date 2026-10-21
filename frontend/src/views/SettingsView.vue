<template>
  <div class="max-w-3xl space-y-6">
    <!-- Header -->
    <div class="bg-white rounded-xl p-5 border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
      <div>
        <h2 class="text-sm font-semibold text-slate-900 tracking-tight">Pengaturan Ekspedisi & Gateway Biteship</h2>
        <p class="text-xs text-slate-500">Konfigurasi API Key pihak ketiga untuk cek tarif, booking pengiriman, dan lacak resi otomatis</p>
      </div>
      <button
        @click="testConnection"
        :disabled="testing"
        class="px-3.5 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-medium transition flex items-center space-x-1.5"
      >
        <Zap :size="13" :class="testing ? 'animate-spin' : ''" />
        <span>{{ testing ? 'Menguji...' : 'Uji Koneksi API' }}</span>
      </button>
    </div>

    <!-- Form -->
    <div class="bg-white rounded-xl p-6 border border-slate-200 space-y-6 text-xs">
      <!-- Enable toggle -->
      <div class="flex items-center justify-between pb-4 border-b border-slate-100">
        <div>
          <span class="font-semibold text-slate-900 text-sm block">Aktifkan Integrasi Biteship</span>
          <span class="text-slate-500 text-[11px]">Gunakan Biteship untuk pelacakan resi live dan estimasi ongkir</span>
        </div>
        <label class="relative inline-flex items-center cursor-pointer">
          <input type="checkbox" v-model="form.enabled" class="sr-only peer" />
          <div class="w-10 h-5 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-slate-900"></div>
        </label>
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
          <span class="text-[10px] text-slate-400 mt-1 block">Dapatkan API Key di dashboard.biteship.com</span>
        </div>
      </div>

      <!-- Auto Tracking & Sync Interval -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-4 border-t border-slate-100">
        <div>
          <label class="block font-semibold text-slate-700 uppercase tracking-wider text-[10px] mb-1.5">
            Background Auto-Tracking Resi
          </label>
          <div class="flex items-center space-x-2 mt-2">
            <input type="checkbox" id="chk-auto" v-model="form.auto_tracking" class="rounded border-slate-300 text-slate-900 focus:ring-0 cursor-pointer" />
            <label for="chk-auto" class="text-slate-700 font-medium">Sinkronisasi status resi secara otomatis</label>
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
        <p class="text-[11px] text-slate-400 mt-1">
          Tempel URL ini di menu Developer &gt; Webhook pada dashboard Biteship untuk sinkronisasi otomatis status resi (order.status, order.waybill_id).
        </p>
      </div>

      <div class="pt-4 border-t border-slate-100">
        <label class="block font-semibold text-slate-700 uppercase tracking-wider text-[10px] mb-1.5">
          Webhook Secret Token (Opsional)
        </label>
        <input
          v-model="form.webhook_secret"
          type="password"
          placeholder="Kosongkan jika tidak menggunakan header signature"
          class="w-full px-3 py-2 rounded-lg border border-slate-200 focus:outline-none focus:border-slate-400 text-slate-800 text-xs"
        />
      </div>

      <!-- Supported Couriers -->
      <div class="pt-4 border-t border-slate-100">
        <label class="block font-semibold text-slate-700 uppercase tracking-wider text-[10px] mb-1.5">
          Kurir yang Didukung
        </label>
        <textarea
          v-model="form.supported_couriers"
          rows="2"
          class="w-full px-3 py-2 rounded-lg border border-slate-200 focus:outline-none focus:border-slate-400 text-xs font-mono text-slate-800"
          placeholder="jne, jnt, sicepat, anteraja, ninja, pos, sentral, wahana..."
        ></textarea>
      </div>

      <!-- Save Button -->
      <div class="pt-4 border-t border-slate-100 flex justify-end">
        <button
          type="button"
          @click="saveSettings"
          :disabled="saving"
          class="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white font-medium rounded-lg transition flex items-center space-x-1.5"
        >
          <Save :size="13" />
          <span>{{ saving ? 'Menyimpan...' : 'Simpan Pengaturan' }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { Zap, Save } from 'lucide-vue-next'
import { DeliveryApi, callApi } from '@/api'

const saving = ref(false)
const testing = ref(false)
const copied = ref(false)
const webhookUrl = ref(window.location.origin + '/api/method/delivery_app.services.biteship.handle_webhook')

const form = reactive({
  enabled: true,
  environment: 'Sandbox',
  api_key: '',
  webhook_secret: '',
  auto_tracking: true,
  sync_interval_hours: 3,
  supported_couriers: 'jne, jnt, sicepat, anteraja, ninja, pos, sentral, wahana, tiki, idexpress, lion, gosend, grab',
})

function copyWebhookUrl() {
  if (navigator?.clipboard?.writeText) {
    navigator.clipboard.writeText(webhookUrl.value)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
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
    alert('Pengaturan Biteship berhasil disimpan.')
  } catch (err) {
    alert(err.message || 'Gagal menyimpan pengaturan')
  } finally {
    saving.value = false
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
})
</script>