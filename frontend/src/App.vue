<template>
  <div class="flex h-screen bg-slate-50 font-sans antialiased text-slate-800 overflow-hidden">
    <!-- Sidebar (Minimalist Fleet Operations Console) -->
    <aside class="w-64 bg-slate-950 text-slate-300 flex flex-col border-r border-slate-850 flex-shrink-0 select-none">
      <!-- App Brand -->
      <div class="h-16 px-5 border-b border-slate-800 flex items-center justify-between">
        <div class="flex items-center space-x-3">
          <div class="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-200">
            <Truck :size="16" class="text-sky-400" />
          </div>
          <div>
            <div class="flex items-center space-x-2">
              <span class="font-bold text-sm text-white tracking-tight">Delivery App</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Navigation Links -->
      <nav class="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <button
          v-for="item in navItems"
          :key="item.id"
          @click="navigate(item.id)"
          :class="[
            'w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-xs font-medium transition',
            currentView === item.id
              ? 'bg-slate-800 text-white font-semibold'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          ]"
        >
          <div class="flex items-center space-x-3">
            <component :is="item.icon" :size="15" :class="currentView === item.id ? 'text-sky-400' : 'text-slate-400'" />
            <span>{{ item.label }}</span>
          </div>
          <span
            v-if="item.badge !== undefined && item.badge > 0"
            class="px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-800 text-slate-300 border border-slate-700"
          >
            {{ item.badge }}
          </span>
        </button>
      </nav>

      <!-- Bottom User & Links -->
      <div class="p-3 border-t border-slate-850 space-y-1.5">
        <a
          href="/driver"
          target="_blank"
          class="flex items-center justify-between px-3 py-2 rounded-lg text-xs text-slate-300 bg-slate-900 hover:bg-slate-850 hover:text-white transition border border-slate-800 font-normal"
        >
          <div class="flex items-center space-x-2.5">
            <Smartphone :size="14" class="text-slate-400" />
            <span>Driver Navigator</span>
          </div>
          <ExternalLink :size="12" class="text-slate-500" />
        </a>

        <a
          href="/app"
          class="flex items-center justify-between px-3 py-2 rounded-lg text-xs text-slate-300 hover:bg-slate-900 hover:text-white transition border border-transparent font-normal"
        >
          <div class="flex items-center space-x-2.5">
            <Building2 :size="14" class="text-slate-400" />
            <span>ERPNext Desk</span>
          </div>
          <ExternalLink :size="12" class="text-slate-500" />
        </a>

        <!-- Logged In User Pill -->
        <div class="pt-2 border-t border-slate-850 flex items-center justify-between px-2 text-xs">
          <div class="flex items-center space-x-2.5 truncate">
            <div class="w-6 h-6 rounded-md bg-slate-800 border border-slate-700 flex items-center justify-center text-[10px] text-slate-200 font-semibold">
              {{ userName.charAt(0).toUpperCase() }}
            </div>
            <span class="truncate text-slate-300 font-medium text-[11px]">{{ userName }}</span>
          </div>
          <a href="/login" class="text-slate-500 hover:text-rose-400 transition" title="Keluar">
            <LogOut :size="13" />
          </a>
        </div>
      </div>
    </aside>

    <!-- Main Content Area -->
    <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
      <!-- Topbar Header -->
      <header class="h-16 bg-white border-b border-slate-200 px-8 flex items-center justify-between flex-shrink-0">
        <div class="flex items-center space-x-2.5">
          <h2 class="text-sm font-semibold text-slate-900 tracking-tight">
            {{ currentNavTitle }}
          </h2>
          <span class="text-xs text-slate-400">/ Logistics & Dispatch</span>
        </div>

        <div class="flex items-center space-x-3">
          <span class="inline-flex items-center space-x-2 px-2.5 py-1 rounded-md text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200/80">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            <span>Live Dispatch Active</span>
          </span>
        </div>
      </header>

      <!-- View Container -->
      <main class="flex-1 overflow-y-auto p-8">
        <transition name="fade" mode="out-in">
          <component
            :is="activeComponent"
            @nav="navigate"
            @open-note="handleOpenNoteFromDashboard"
          />
        </transition>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import {
  Truck,
  LayoutDashboard,
  Package,
  Route,
  ShieldCheck,
  Users,
  Settings,
  Smartphone,
  Building2,
  ExternalLink,
  LogOut
} from 'lucide-vue-next'
import DashboardView from '@/views/DashboardView.vue'
import DeliveryNotesView from '@/views/DeliveryNotesView.vue'
import DeliveryTripsView from '@/views/DeliveryTripsView.vue'
import PodGalleryView from '@/views/PodGalleryView.vue'
import FleetResourcesView from '@/views/FleetResourcesView.vue'
import SettingsView from '@/views/SettingsView.vue'
import { DeliveryApi } from '@/api'

const currentView = ref('dashboard')
const userName = ref(window.workspace_user || 'Operator')
const pendingCount = ref(0)

const navItems = computed(() => [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'notes', label: 'Delivery Notes (Orders)', icon: Package, badge: pendingCount.value },
  { id: 'trips', label: 'Delivery Trips (Rute)', icon: Route },
  { id: 'pod', label: 'Proof of Delivery (POD)', icon: ShieldCheck },
  { id: 'fleet', label: 'Armada & Driver', icon: Users },
  { id: 'settings', label: 'Pengaturan Ekspedisi', icon: Settings },
])

const currentNavTitle = computed(() => {
  const item = navItems.value.find(i => i.id === currentView.value)
  return item ? item.label : 'Operations'
})

const activeComponent = computed(() => {
  switch (currentView.value) {
    case 'dashboard': return DashboardView
    case 'notes': return DeliveryNotesView
    case 'trips': return DeliveryTripsView
    case 'pod': return PodGalleryView
    case 'fleet': return FleetResourcesView
    case 'settings': return SettingsView
    default: return DashboardView
  }
})

function navigate(viewId) {
  currentView.value = viewId
  window.location.hash = `#/${viewId}`
}

function handleOpenNoteFromDashboard(noteId) {
  currentView.value = 'notes'
  window.location.hash = `#/notes`
}

function syncFromHash() {
  const hash = window.location.hash.replace(/^#\/?/, '')
  if (['dashboard', 'notes', 'trips', 'pod', 'fleet', 'settings'].includes(hash)) {
    currentView.value = hash
  }
}

async function updatePendingBadge() {
  try {
    const res = await DeliveryApi.getSummary()
    if (res?.kpi?.pending_orders) {
      pendingCount.value = res.kpi.pending_orders
    }
  } catch (e) {
    console.warn('Badge update failed:', e)
  }
}

onMounted(() => {
  syncFromHash()
  window.addEventListener('hashchange', syncFromHash)
  updatePendingBadge()
})
</script>

<style>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
