<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4"
  >
    <div
      class="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh] animate-in fade-in zoom-in-95 duration-150"
    >
      <!-- Header -->
      <div class="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
        <div class="flex items-center space-x-2.5">
          <div class="w-8 h-8 rounded-lg bg-sky-100 text-sky-700 flex items-center justify-center font-medium">
            <Package :size="16" />
          </div>
          <div>
            <h3 class="text-sm font-semibold text-slate-900">
              Proses Intake Sales Order
            </h3>
            <p class="text-xs text-slate-500">
              Buat dan submit Delivery Note penuh dari pesanan pelanggan
            </p>
          </div>
        </div>
        <button
          @click="close"
          class="p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200 transition"
        >
          <X :size="16" />
        </button>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="p-12 text-center text-slate-500 text-xs">
        <div class="inline-block animate-spin mb-2">
          <RefreshCw :size="20" class="text-sky-600" />
        </div>
        <div>Memuat rincian Sales Order...</div>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="p-6">
        <div class="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs flex items-start space-x-2.5">
          <AlertCircle :size="16" class="flex-shrink-0 mt-0.5" />
          <div>
            <div class="font-semibold">Terjadi Kesalahan</div>
            <div class="mt-1">{{ error }}</div>
          </div>
        </div>
        <div class="mt-4 flex justify-end">
          <button
            @click="close"
            class="px-3.5 py-1.5 rounded-lg border border-slate-200 text-xs font-medium text-slate-600 hover:bg-slate-50 transition"
          >
            Tutup
          </button>
        </div>
      </div>

      <!-- Modal Body -->
      <div v-else-if="soDetail" class="flex-1 overflow-y-auto p-6 space-y-5 text-xs text-slate-700">
        <!-- Order Header Overview -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 bg-slate-50 border border-slate-200 rounded-xl">
          <div>
            <span class="text-slate-400 block text-[11px]">No. Pesanan:</span>
            <span class="font-bold text-slate-900 font-mono text-xs">{{ soDetail.name }}</span>
          </div>
          <div>
            <span class="text-slate-400 block text-[11px]">Company:</span>
            <span class="font-semibold text-slate-900 truncate block">{{ soDetail.company }}</span>
          </div>
          <div>
            <span class="text-slate-400 block text-[11px]">Tgl Pengiriman:</span>
            <span class="font-semibold text-slate-900">{{ formatDate(soDetail.delivery_date) }}</span>
          </div>
          <div>
            <span class="text-slate-400 block text-[11px]">Total Nilai:</span>
            <span class="font-bold text-sky-700">Rp {{ formatCurrency(soDetail.grand_total) }}</span>
          </div>
        </div>

        <!-- Customer & Destination -->
        <div class="p-4 border border-slate-200 rounded-xl space-y-2">
          <div class="flex items-start justify-between">
            <div class="flex items-start space-x-2">
              <MapPin :size="15" class="text-slate-400 mt-0.5 flex-shrink-0" />
              <div>
                <div class="font-semibold text-slate-900">{{ soDetail.customer_name || soDetail.customer }}</div>
                <div class="text-[11px] text-slate-500 mt-0.5 leading-relaxed">{{ soDetail.shipping_address || '-' }}</div>
              </div>
            </div>
            <span
              :class="[
                'px-2 py-0.5 rounded text-[10px] font-medium border flex-shrink-0',
                soDetail.has_customer_coordinates
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : 'bg-amber-50 text-amber-700 border-amber-200'
              ]"
            >
              {{ soDetail.has_customer_coordinates ? 'Koordinat Terisi' : 'Koordinat Belum Ada' }}
            </span>
          </div>
        </div>

        <!-- Items Table -->
        <div>
          <div class="flex items-center justify-between mb-2">
            <h4 class="font-semibold text-slate-900 text-xs">
              Daftar Barang (Pengiriman Penuh 100%)
            </h4>
            <span class="text-[11px] text-slate-500">
              Total: {{ soDetail.items?.length || 0 }} Item
            </span>
          </div>

          <div class="border border-slate-200 rounded-xl overflow-hidden">
            <table class="w-full text-left border-collapse text-xs">
              <thead class="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold text-[10px] uppercase">
                <tr>
                  <th class="p-2.5">Item</th>
                  <th class="p-2.5 text-center">Qty</th>
                  <th class="p-2.5">Gudang Pengambilan</th>
                  <th class="p-2.5 text-right">Subtotal</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100">
                <tr v-for="(it, idx) in soDetail.items" :key="idx" class="hover:bg-slate-50/60">
                  <td class="p-2.5">
                    <div class="font-medium text-slate-900">{{ it.item_name || it.item_code }}</div>
                    <div class="text-[10px] font-mono text-slate-400">{{ it.item_code }}</div>
                  </td>
                  <td class="p-2.5 text-center font-bold text-slate-800">
                    {{ it.qty }} {{ it.uom }}
                  </td>
                  <td class="p-2.5 text-slate-600 text-[11px]">
                    {{ it.warehouse || 'Gudang Default' }}
                  </td>
                  <td class="p-2.5 text-right font-medium text-slate-700">
                    Rp {{ formatCurrency(it.amount) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Delivery Method Selector -->
        <div class="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
          <label class="block font-semibold text-slate-900 text-xs">
            Metode Pengiriman:
          </label>
          <div class="grid grid-cols-2 gap-3">
            <label
              :class="[
                'flex items-start space-x-3 p-3 rounded-lg border cursor-pointer transition',
                deliveryMethod === 'Armada Sendiri'
                  ? 'bg-sky-50/50 border-sky-400 ring-1 ring-sky-400'
                  : 'bg-white border-slate-200 hover:border-slate-300'
              ]"
            >
              <input
                type="radio"
                value="Armada Sendiri"
                v-model="deliveryMethod"
                class="mt-0.5 text-sky-600 focus:ring-0 cursor-pointer"
              />
              <div>
                <div class="font-semibold text-slate-900 flex items-center space-x-1.5">
                  <Truck :size="13" class="text-sky-600" />
                  <span>Armada Sendiri</span>
                </div>
                <div class="text-[11px] text-slate-500 mt-0.5">
                  Dijadwalkan ke rute multi-drop Delivery Trip internal
                </div>
              </div>
            </label>

            <label
              :class="[
                'flex items-start space-x-3 p-3 rounded-lg border cursor-pointer transition',
                deliveryMethod === 'Ekspedisi'
                  ? 'bg-indigo-50/50 border-indigo-400 ring-1 ring-indigo-400'
                  : 'bg-white border-slate-200 hover:border-slate-300'
              ]"
            >
              <input
                type="radio"
                value="Ekspedisi"
                v-model="deliveryMethod"
                class="mt-0.5 text-indigo-600 focus:ring-0 cursor-pointer"
              />
              <div>
                <div class="font-semibold text-slate-900 flex items-center space-x-1.5">
                  <Send :size="13" class="text-indigo-600" />
                  <span>Ekspedisi (3PL)</span>
                </div>
                <div class="text-[11px] text-slate-500 mt-0.5">
                  Kirim lewat kurir logistik pihak ketiga (JNE, SiCepat, dll.)
                </div>
              </div>
            </label>
          </div>
        </div>

        <!-- Submission Error Alert -->
        <div v-if="submitError" class="p-3 bg-rose-50 border border-rose-200 rounded-lg text-rose-700 text-xs flex items-start space-x-2">
          <AlertCircle :size="14" class="flex-shrink-0 mt-0.5" />
          <div>
            <div class="font-semibold">Validasi ERPNext Gagal:</div>
            <div class="mt-0.5">{{ submitError }}</div>
          </div>
        </div>
      </div>

      <!-- Footer Actions -->
      <div class="px-6 py-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
        <div class="text-xs text-slate-500">
          Status: <strong class="text-slate-800">1 SO = 1 DN Penuh</strong>
        </div>
        <div class="flex items-center space-x-2">
          <button
            type="button"
            @click="close"
            :disabled="submitting"
            class="px-3.5 py-2 rounded-lg text-xs font-medium text-slate-600 hover:bg-slate-200 transition"
          >
            Batal
          </button>
          <button
            type="button"
            @click="handleSubmit"
            :disabled="submitting || !soDetail?.is_eligible"
            class="px-4 py-2 rounded-lg text-xs font-medium bg-sky-600 hover:bg-sky-700 text-white transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-1.5 shadow-xs"
          >
            <RefreshCw v-if="submitting" :size="13" class="animate-spin" />
            <Check v-else :size="13" />
            <span>{{ submitting ? 'Memproses Delivery Note...' : 'Buat & Submit Delivery Note' }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import {
  Package,
  X,
  RefreshCw,
  AlertCircle,
  MapPin,
  Truck,
  Send,
  Check
} from 'lucide-vue-next'
import { DeliveryApi } from '@/api'

const props = defineProps({
  isOpen: Boolean,
  salesOrderId: String,
})

const emit = defineEmits(['close', 'created'])

const loading = ref(false)
const submitting = ref(false)
const error = ref(null)
const submitError = ref(null)
const soDetail = ref(null)
const deliveryMethod = ref('Armada Sendiri')

async function loadDetail() {
  if (!props.salesOrderId) return
  loading.value = true
  error.value = null
  submitError.value = null
  try {
    const res = await DeliveryApi.getSalesOrderDetail(props.salesOrderId)
    soDetail.value = res
  } catch (err) {
    error.value = err.message || 'Gagal memuat rincian Sales Order'
  } finally {
    loading.value = false
  }
}

async function handleSubmit() {
  if (!props.salesOrderId) return
  submitting.value = true
  submitError.value = null
  try {
    const res = await DeliveryApi.createDeliveryNoteFromSo({
      sales_order: props.salesOrderId,
      delivery_method: deliveryMethod.value,
    })
    emit('created', res)
    close()
  } catch (err) {
    submitError.value = err.message || 'Gagal membuat Delivery Note'
  } finally {
    submitting.value = false
  }
}

function close() {
  emit('close')
}

function formatDate(val) {
  if (!val) return '-'
  try {
    const d = new Date(val)
    return d.toLocaleDateString('id-ID', { day: '2-digit', month: 'short', year: 'numeric' })
  } catch {
    return val
  }
}

function formatCurrency(val) {
  return Number(val || 0).toLocaleString('id-ID')
}

watch(() => props.isOpen, (open) => {
  if (open) {
    deliveryMethod.value = 'Armada Sendiri'
    loadDetail()
  } else {
    soDetail.value = null
    error.value = null
    submitError.value = null
  }
})
</script>
