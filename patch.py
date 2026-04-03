import re

with open('/tmp/stitch_ui.html', 'r') as f:
    html = f.read()

# Sensors
html = html.replace('<h3 class="text-3xl font-bold text-on-surface mt-1">28°C</h3>', '<div class="flex items-baseline gap-1 mt-1"><h3 class="text-3xl font-bold text-on-surface" id="val-temp">--</h3><span class="text-xl">°C</span></div>')
html = html.replace('<h3 class="text-3xl font-bold text-on-surface mt-1">65%</h3>', '<div class="flex items-baseline gap-1 mt-1"><h3 class="text-3xl font-bold text-on-surface" id="val-hum">--</h3><span class="text-xl">%</span></div>')
html = html.replace('<h3 class="text-3xl font-bold text-on-surface mt-1">312 ADC</h3>', '<div class="flex items-baseline gap-1 mt-1"><h3 class="text-3xl font-bold text-on-surface" id="val-moist">--</h3><span class="text-xl">ADC</span></div>')
html = html.replace('<h3 class="text-3xl font-bold text-on-surface mt-1">185 Lux</h3>', '<div class="flex items-baseline gap-1 mt-1"><h3 class="text-3xl font-bold text-on-surface" id="val-lux">--</h3><span class="text-xl">Lux</span></div>')

# Status / Header
html = html.replace('<p class="text-primary font-semibold tracking-wider text-xs uppercase mb-1">System Live</p>', '<p class="text-primary font-semibold tracking-wider text-xs uppercase mb-1" id="badge-mode">System Live</p>')
html = html.replace('Environmental Control</h2>', 'Environmental Control</h2>\n<p class="text-sm text-on-surface-variant font-mono mt-2" id="val-data-count">Data Points: 0</p>')

html = html.replace('<span class="flex h-2 w-2 rounded-full bg-primary animate-pulse"></span>', '<span class="flex h-2 w-2 rounded-full bg-primary animate-pulse" id="conn-dot"></span>')

# Relays
html = html.replace('<p class="text-xs text-primary font-medium">ON</p>', '<p class="text-xs text-primary font-medium" id="badge-pump">--</p>', 1)
html = html.replace('<input checked="" class="sr-only peer" type="checkbox"/>', '<input class="sr-only peer" type="checkbox" id="toggle-pump" disabled/>', 1)

html = html.replace('<p class="text-xs text-primary font-medium">ON</p>', '<p class="text-xs text-primary font-medium" id="badge-light">--</p>', 1)
html = html.replace('<input checked="" class="sr-only peer" type="checkbox"/>', '<input class="sr-only peer" type="checkbox" id="toggle-light" disabled/>', 1)

html = html.replace('<p class="text-xs text-on-surface-variant font-medium">OFF</p>', '<p class="text-xs text-on-surface-variant font-medium" id="badge-fan">--</p>', 1)
html = html.replace('<input class="sr-only peer" type="checkbox"/>', '<input class="sr-only peer" type="checkbox" id="toggle-fan" disabled/>', 1)

js_block = """
<!-- ══ LIVE POLLING JS ══ -->
<script>
const POLL_MS = 5000;
async function poll() {
  try {
    const res = await fetch('/status');
    if (!res.ok) throw new Error(res.status);
    const d = await res.json();
    updateSensors(d);
    updateRelays(d);
    updateEngineStatus(d);
    setConn(true, d.timestamp);
  } catch (e) {
    setConn(false);
  }
}
function setVal(id, v, decimals = 1) {
  const el = document.getElementById(id);
  if (el) el.textContent = (v !== null && v !== undefined) ? (typeof v === 'number' ? v.toFixed(decimals) : v) : '--';
}
function updateSensors(d) {
  setVal('val-temp',  d.temp,  1);
  setVal('val-hum',   d.hum,   1);
  setVal('val-moist', d.moist, 0);
  setVal('val-lux',   d.lux,   0);
}
function setRelay(name, state) {
  const badge = document.getElementById('badge-' + name);
  const toggle = document.getElementById('toggle-' + name);
  const on = (state === 1 || state === true);
  if (badge) {
    badge.textContent = on ? 'ON' : 'OFF';
    badge.className = on ? 'text-xs text-primary font-bold transition-all' : 'text-xs text-on-surface-variant font-medium transition-all';
  }
  if (toggle) {
    toggle.checked = on;
  }
}
function updateRelays(d) {
  setRelay('pump',  d.pump);
  setRelay('light', d.light);
  setRelay('fan',   d.fan);
}
function updateEngineStatus(d) {
    const badge = document.getElementById('badge-mode');
    const count = document.getElementById('val-data-count');
    
    if (count && d.data_count !== undefined) {
        count.textContent = `Data Points: ${d.data_count} | Logic Engine Online`;
    }
    
    if (badge && d.mode) {
        if (d.mode === 'ML') {
            badge.textContent = 'AI Mode Active';
            badge.className = 'text-primary font-bold tracking-wider text-xs uppercase mb-1 transition-all';
        } else {
            badge.textContent = 'Rule Fallback Active';
            badge.className = 'text-orange-500 font-bold tracking-wider text-xs uppercase mb-1 transition-all';
        }
    }
}
function setConn(online, ts) {
  const dot  = document.getElementById('conn-dot');
  if (dot) dot.className = 'flex h-2 w-2 rounded-full ' + (online ? 'bg-primary animate-pulse' : 'bg-red-500');
}
setInterval(poll, POLL_MS);
poll();
</script>
</body></html>
"""
html = html.replace('</body></html>', js_block)

dst = '/Users/kokkilagaddaabhishek/Desktop/autonomus hive/server/templates/index.html'
with open(dst, 'w') as f:
    f.write(html)
print("PATCHED AND SAVED TO", dst)
