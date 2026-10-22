<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="bg-white rounded-xl p-5 border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
      <div>
        <h2 class="text-sm font-semibold text-slate-900 tracking-tight">Armada & Pengemudi (Fleet Resources)</h2>
        <p class="text-xs text-slate-500">Daftar kendaraan dan pengemudi yang terdaftar di ERPNext</p>
      </div>
      <div class="flex items-center space-x-2">
        <a
          href="/app/driver"
          target="_blank"
          class="px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-xs font-medium text-slate-700 transition inline-flex items-center space-x-1.5"
        >
          <Plus :size="12" />
          <span>Tambah Driver di Desk</span>
          <ExternalLink :size="10" class="text-slate-400" />
        </a>
        <a
          href="/app/vehicle"
          target="_blank"
          class="px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-xs font-medium text-slate-700 transition inline-flex items-center space-x-1.5"
        >
          <Plus :size="12" />
          <span>Tambah Kendaraan di Desk</span>
          <ExternalLink :size="10" class="text-slate-400" />
        </a>
      </div>
    </div>

    <!-- Drivers & Vehicles Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <!-- Drivers Column -->
      <div class="bg-white rounded-xl p-5 border border-slate-200 space-y-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-2.5">
            <div class="w-7 h-7 rounded-md bg-slate-100 flex items-center justify-center text-slate-600">
              <Users :size="15" />
            </div>
            <h3 class="font-semibold text-sm text-slate-900">Daftar Driver ({{ drivers.length }})</h3>
          </div>
        </div>

        <div class="space-y-2.5">
          <div
            v-for="d in drivers"
            :key="d.name"
            class="p-4 rounded-lg border border-slate-200 bg-slate-50/60 flex items-center justify-between text-xs"
          >
            <div>
              <span class="font-semibold text-slate-900 text-sm block">{{ d.full_name }}</span>
              <span class="text-slate-500 text-[11px] block mt-0.5">{{ d.name }}</span>
              <span v-if="d.cell_number" class="text-slate-600 inline-flex items-center space-x-1 text-[11px] mt-1">
                <Phone :size="11" class="text-slate-400" />
                <span>{{ d.cell_number }}</span>
              </span>
            </div>
            <div class="text-right">
              <span class="px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200/80">
                Aktif
              </span>
              <div class="mt-2">
                <a
                  :href="`/app/driver/${d.name}`"
                  target="_blank"
                  class="text-[11px] text-sky-600 hover:underline font-medium inline-flex items-center space-x-1"
                >
                  <span>Edit</span>
                  <ExternalLink :size="10" />
                </a>
              </div>
            </div>
          </div>

          <div v-if="drivers.length === 0" class="text-center py-8 text-slate-400 text-xs">
            Belum ada driver yang terdaftar.
          </div>
        </div>
      </div>

      <!-- Vehicles Column -->
      <div class="bg-white rounded-xl p-5 border border-slate-200 space-y-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-2.5">
            <div class="w-7 h-7 rounded-md bg-slate-100 flex items-center justify-center text-slate-600">
              <Truck :size="15" />
            </div>
            <h3 class="font-semibold text-sm text-slate-900">Daftar Kendaraan ({{ vehicles.length }})</h3>
          </div>
        </div>

        <div class="space-y-2.5">
          <div
            v-for="v in vehicles"
            :key="v.name"
            class="p-4 rounded-lg border border-slate-200 bg-slate-50/60 flex items-center justify-between text-xs"
          >
            <div>
              <span class="font-semibold text-slate-900 text-sm block font-mono">{{ v.license_plate }}</span>
              <span class="text-slate-600 font-medium block mt-0.5">{{ v.make }} {{ v.model }}</span>
              <span class="text-slate-400 text-[11px] block mt-0.5">Bahan Bakar: {{ v.fuel_type || '-' }}</span>
            </div>
            <div class="text-right">
              <span class="px-2 py-0.5 rounded text-[10px] font-medium bg-sky-50 text-sky-700 border border-sky-200/80">
                Ready
              </span>
              <div class="mt-2">
                <a
                  :href="`/app/vehicle/${v.name}`"
                  target="_blank"
                  class="text-[11px] text-sky-600 hover:underline font-medium inline-flex items-center space-x-1"
                >
                  <span>Edit</span>
                  <ExternalLink :size="10" />
                </a>
              </div>
            </div>
          </div>

          <div v-if="vehicles.length === 0" class="text-center py-8 text-slate-400 text-xs">
            Belum ada kendaraan yang terdaftar.
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Plus, ExternalLink, Users, Phone, Truck } from 'lucide-vue-next'
import { DeliveryApi } from '@/api'

const drivers = ref([])
const vehicles = ref([])

async function loadData() {
  try {
    const res = await DeliveryApi.getFleetResources()
    drivers.value = res.drivers || []
    vehicles.value = res.vehicles || []
  } catch (e) {
    console.error(e)
  }
}

onMounted(() => {
  loadData()
})
</script>
