<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 overflow-hidden">
    <!-- Backdrop -->
    <div @click="close" class="absolute inset-0 bg-slate-950/60 backdrop-blur-xs transition-opacity"></div>

    <div class="fixed inset-y-0 right-0 pl-10 max-w-full flex">
      <div class="w-screen max-w-lg bg-white shadow-xl flex flex-col border-l border-slate-200">
        <!-- Header -->
        <div class="p-6 bg-slate-900 text-white flex items-center justify-between border-b border-slate-800">
          <div>
            <div class="flex items-center space-x-2">
              <span class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">Delivery Note</span>
              <span
                :class="[
                  'px-2 py-0.5 rounded text-[10px] font-medium uppercase border',
                  note?.custom_delivery_method === 'Ekspedisi'
                    ? 'bg-indigo-500/10 text-indigo-300 border-indigo-500/30'
                    : 'bg-sky-500/10 text-sky-300 border-sky-500/30'
                ]"
              >
                {{ trackingMethodLabel(note?.custom_delivery_method) }}
              </span>
            </div>
            <h2 class="text-base font-semibold tracking-tight mt-1">{{ note?.name }}</h2>
          </div>
          <button @click="close" class="text-slate-400 hover:text-white p-1 rounded-lg transition">
            <X :size="16" />
          </button>
        </div>

        <!-- Body Content -->
        <div class="flex-1 p-6 space-y-6 overflow-y-auto text-xs text-slate-700">
          <!-- Status Banner -->
          <div class="p-4 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between">
            <div>
              <span class="text-[11px] text-slate-400 font-medium block">Status Pengiriman</span>
              <span class="text-sm font-semibold text-slate-800">
                {{ getDeliveryStatus(note) }}
              </span>
            </div>
            <div class="text-right">
              <span class="text-[11px] text-slate-400 font-medium block">Total Nilai</span>
              <span class="text-sm font-semibold text-slate-900">
                Rp {{ Number(note?.grand_total || 0).toLocaleString('id-ID') }}
              </span>
            </div>
          </div>

          <!-- Customer & Address -->
          <div>
            <h4 class="font-semibold text-slate-900 uppercase tracking-wider text-[10px] mb-2 flex items-center space-x-1.5">
              <User :size="13" class="text-slate-500" />
              <span>Informasi Pelanggan & Alamat</span>
            </h4>
            <div class="p-4 rounded-lg border border-slate-200 space-y-2 bg-white">
              <div class="font-semibold text-slate-900 text-sm">{{ note?.customer_name || note?.customer }}</div>
              <div v-if="note?.contact_mobile" class="flex items-center space-x-2 text-slate-600">
                <span class="inline-flex items-center space-x-1">
                  <Phone :size="12" class="text-slate-400" />
                  <span>{{ note?.contact_mobile }}</span>
                </span>
                <a
                  :href="`https://wa.me/${cleanPhone(note?.contact_mobile)}`"
                  target="_blank"
                  class="px-2 py-0.5 bg-emerald-50 text-emerald-700 font-medium rounded text-[10px] border border-emerald-200 hover:bg-emerald-100 transition"
                >
                  WhatsApp
                </a>
              </div>
              <div class="text-slate-600 leading-relaxed border-t border-slate-100 pt-2 whitespace-pre-line">
                {{ note?.clean_address || note?.address_display || note?.shipping_address || 'Alamat tidak tersedia' }}
              </div>
            </div>
          </div>

          <!-- Items Table -->
          <div>
            <h4 class="font-semibold text-slate-900 uppercase tracking-wider text-[10px] mb-2 flex items-center space-x-1.5">
              <Package :size="13" class="text-slate-500" />
              <span>Rincian Barang ({{ note?.items?.length || 0 }} Item)</span>
            </h4>
            <div class="border border-slate-200 rounded-lg overflow-hidden">
              <table class="w-full text-left border-collapse">
                <thead class="bg-slate-50 text-slate-500 font-medium text-[11px] border-b border-slate-200">
                  <tr>
                    <th class="p-2.5">Produk</th>
                    <th class="p-2.5 text-right">Qty</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100">
                  <tr v-for="item in note?.items" :key="item.item_code" class="hover:bg-slate-50/50">
                    <td class="p-2.5">
                      <div class="font-medium text-slate-800">{{ item.item_name }}</div>
                      <div class="text-[10px] text-slate-400 font-mono">{{ item.item_code }}</div>
                    </td>
                    <td class="p-2.5 text-right font-semibold text-slate-900">
                      {{ item.qty }} <span class="font-normal text-slate-500 text-[10px]">{{ item.uom }}</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Logistics Flow Specifics -->
          <!-- A. Ekspedisi -->
          <div v-if="note?.custom_delivery_method === 'Ekspedisi'" class="space-y-3">
            <h4 class="font-semibold text-slate-900 uppercase tracking-wider text-[10px] flex items-center space-x-1.5">
              <Send :size="13" class="text-slate-500" />
              <span>Status Ekspedisi (Biteship)</span>
            </h4>
            <div class="p-4 rounded-lg border border-slate-200 bg-slate-50/50 space-y-2">
              <div class="flex justify-between items-center">
                <span class="font-semibold text-slate-900">{{ note?.custom_courier_code?.toUpperCase() }}</span>
                <span class="font-mono text-slate-800 font-medium px-2 py-0.5 bg-white rounded border border-slate-200">
                  {{ note?.custom_waybill_no || 'Belum ada resi' }}
                </span>
              </div>
              <div class="flex justify-between items-center pt-2 border-t border-slate-100 text-[11px]">
                <span class="text-slate-600">Pelacakan Live:</span>
                <button
                  v-if="note?.custom_waybill_no"
                  @click="$emit('track', note)"
                  class="font-medium text-sky-600 hover:text-sky-800 inline-flex items-center space-x-1"
                >
                  <span>Buka Timeline Lacak Resi</span>
                  <ExternalLink :size="10" />
                </button>
              </div>
            </div>
          </div>

          <!-- B. Armada Sendiri / Trip -->
          <div v-else class="space-y-3">
            <h4 class="font-semibold text-slate-900 uppercase tracking-wider text-[10px] flex items-center space-x-1.5">
              <Truck :size="13" class="text-slate-500" />
              <span>Checkpoint & Rute Pengiriman</span>
            </h4>
            <div v-if="note?.trip" class="p-4 rounded-lg border border-slate-200 bg-slate-50/50 space-y-2">
              <div class="flex justify-between items-center">
                <span class="font-semibold text-slate-900">{{ note.trip.trip_name }}</span>
                <span class="px-2 py-0.5 rounded text-[10px] font-medium bg-white text-slate-800 border border-slate-200">
                  {{ note.trip.trip_status }}
                </span>
              </div>
              <div class="text-[11px] text-slate-700">
                Driver: <strong>{{ note.trip.driver_name || '-' }}</strong> · Kendaraan: <strong>{{ note.trip.vehicle || '-' }}</strong>
              </div>
            </div>
            <div v-else class="p-4 rounded-lg border border-slate-200 bg-slate-50 text-slate-600 text-[11px]">
              Belum ditugaskan ke Delivery Trip mana pun.
            </div>

            <!-- POD Info if available -->
            <div v-if="note?.pod || note?.custom_proof_of_delivery" class="p-4 rounded-lg border border-emerald-200 bg-emerald-50/50">
              <div class="flex justify-between items-center">
                <span class="font-semibold text-emerald-900">Proof of Delivery (POD)</span>
                <button
                  @click="$emit('view-pod', note)"
                  class="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded font-medium text-[11px] transition inline-flex items-center space-x-1"
                >
                  <ShieldCheck :size="12" />
                  <span>Lihat Bukti Foto & TTD</span>
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Footer Actions -->
        <div class="p-4 bg-slate-50 border-t border-slate-200 flex flex-wrap gap-2 justify-end">
          <a
            :href="`/app/delivery-note/${note?.name}`"
            target="_blank"
            class="px-3 py-1.5 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-100 text-xs font-medium transition inline-flex items-center space-x-1"
          >
            <span>Buka di ERPNext Desk</span>
            <ExternalLink :size="11" />
          </a>
          <button
            v-if="!note?.custom_waybill_no && note?.custom_delivery_method !== 'Ekspedisi'"
            @click="$emit('dispatch-ekspedisi', note)"
            class="px-3.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-medium transition inline-flex items-center space-x-1.5"
          >
            <Send :size="12" />
            <span>Kirim Ekspedisi (3PL)</span>
          </button>
          <button
            v-if="!note?.trip && note?.custom_delivery_method === 'Armada Sendiri'"
            @click="$emit('add-to-trip', note)"
            class="px-3.5 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-700 text-white text-xs font-medium transition inline-flex items-center space-x-1.5"
          >
            <Truck :size="12" />
            <span>Tugaskan ke Trip</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { X, User, Phone, Package, Send, Truck, ShieldCheck, ExternalLink } from 'lucide-vue-next'
import { trackingMethodLabel } from '@/utils/tracking'

const props = defineProps({
  isOpen: Boolean,
  note: Object
})

const emit = defineEmits(['close', 'dispatch-ekspedisi', 'add-to-trip', 'track', 'view-pod'])

function getDeliveryStatus(n) {
  if (!n) return '-'
  if (n.custom_delivery_method === 'Ekspedisi') {
    return n.custom_tracking_status || 'Siap Kirim Ekspedisi'
  }
  if (n.custom_pod_status === 'Delivered') return 'Terkirim (POD)'
  if (n.trip?.trip_status === 'In Transit') return 'Dalam Perjalanan (Supir)'
  if (n.trip) return `Terjadwal (${n.trip.trip_status})`
  return 'Siap Dijadwalkan'
}

function cleanPhone(phone) {
  if (!phone) return ''
  let cleaned = phone.replace(/[^0-9]/g, '')
  if (cleaned.startsWith('0')) cleaned = '62' + cleaned.slice(1)
  return cleaned
}

function close() {
  emit('close')
}
</script>
