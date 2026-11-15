import math
import streamlit as st
import streamlit.components.v1 as components

# ============================================================
# MOONBASE: POWER SURVIVAL
# Interactive lunar habitat + solar microgrid design simulator
# All engineering values are illustrative assumptions, not NASA specifications.
# ============================================================

st.set_page_config(
    page_title="MOONBASE | Power Survival",
    page_icon="🌕",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------- STYLE ---------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Orbitron:wght@500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: Inter, sans-serif; }
.stApp {
    background:
      radial-gradient(ellipse at 50% -10%, rgba(66,92,130,.25), transparent 42%),
      linear-gradient(180deg, #080d18 0%, #101827 55%, #171c27 100%);
    color: #edf3ff;
}
.block-container { padding-top: 1.2rem; max-width: 1500px; }
h1, h2, h3 { color: #f4f7ff !important; }
.hero-title { font-family: Orbitron, sans-serif; letter-spacing: 2px; font-weight: 800; }
.subtle { color: #aab8cf; }
.panel {
  background: linear-gradient(145deg, rgba(25,38,58,.94), rgba(13,22,37,.96));
  border: 1px solid rgba(130,165,210,.22);
  border-radius: 16px; padding: 16px 18px; margin-bottom: 12px;
  box-shadow: 0 12px 28px rgba(0,0,0,.18);
}
.metric-label { color:#9fb1ca; font-size: .78rem; text-transform:uppercase; letter-spacing:1px; }
.metric-value { color:#f7faff; font-family:Orbitron,sans-serif; font-size:1.65rem; font-weight:700; }
.metric-note { color:#9fb1ca; font-size:.78rem; }
.status-good { color:#6ee7b7; font-weight:700; }
.status-warn { color:#fbbf24; font-weight:700; }
.status-bad { color:#fb7185; font-weight:700; }
div[data-testid="stMetric"] {
  background: rgba(20,32,50,.85); border: 1px solid rgba(130,165,210,.2);
  padding: 12px 14px; border-radius: 14px;
}
div[data-testid="stMetricLabel"] { color:#9fb1ca; }
div[data-testid="stMetricValue"] { color:#f7faff; }
.stButton>button {
  border-radius: 10px; border:1px solid #3d638c;
  background:linear-gradient(90deg,#1c4770,#256b82); color:white; font-weight:700;
}
.stButton>button:hover { border-color:#80c9e8; color:white; }
div[data-testid="stProgressBar"] > div > div { background:linear-gradient(90deg,#38bdf8,#34d399); }
hr { border-color:rgba(130,165,210,.2); }
</style>
""", unsafe_allow_html=True)

# ----------------------- MODEL DEFAULTS ----------------------
LUNAR_DAY_DAYS = 14.75
LUNAR_CYCLE_DAYS = 29.5
DAYS_AUTONOMY_DEFAULT = 14.0

st.sidebar.markdown("## 🛰️ Mission Control")
st.sidebar.caption("MOONBASE / POWER SURVIVAL")
st.sidebar.markdown("---")

st.sidebar.markdown("### Mission timeline")
lunar_day = st.sidebar.slider(
    "Lunar cycle day",
    min_value=0.0, max_value=29.5, value=18.0, step=0.25,
    help="0–14.75: lunar daylight. 14.75–29.5: lunar night.",
)
is_daylight = lunar_day < LUNAR_DAY_DAYS
if is_daylight:
    phase = "DAYLIGHT"
    phase_elapsed = lunar_day
else:
    phase = "LUNAR NIGHT"
    phase_elapsed = lunar_day - LUNAR_DAY_DAYS

st.sidebar.markdown("### Solar system design")
pv_kw = st.sidebar.slider("Installed PV capacity (kW)", 10, 250, 100, 5)
peak_sun_hours = st.sidebar.slider("Equivalent full-sun hours / day", 2.0, 7.0, 4.5, 0.25)
derate = st.sidebar.slider("PV system derating", 0.50, 0.95, 0.75, 0.01)
battery_nominal = st.sidebar.slider("Battery nominal capacity (kWh)", 500, 6000, 2500, 100)
dod = st.sidebar.slider("Maximum battery depth of discharge (DoD)", 0.50, 0.90, 0.80, 0.01)
battery_eff = st.sidebar.slider("Battery discharge efficiency", 0.80, 0.99, 0.92, 0.01)

st.sidebar.markdown("### Crew")
crew = st.sidebar.selectbox("Crew size", [1, 2, 3, 4, 5, 6], index=2)
st.sidebar.caption("The default mission concept uses 3 astronauts.")

# -------------------------- LOADS -----------------------------
st.title("🌕 MOONBASE: POWER SURVIVAL")
st.markdown("**Lunar habitat energy command center**  ·  Solar generation · Battery storage · Critical loads")
st.caption("Interactive concept simulator for a lunar surface base. Engineering values are simplified assumptions for the challenge demo.")

default_loads = {
    "Oxygen Generation": (1.20, True, "Oxygen production and cabin atmosphere support"),
    "CO2 Removal System": (0.45, True, "Carbon-dioxide scrubbing and air revitalization"),
    "Water Recovery": (0.65, True, "Water purification and recycling pumps"),
    "Thermal Control / Heaters": (2.80, True, "Habitat heating and temperature regulation"),
    "Main Communications": (0.25, True, "Primary Earth link and mission telemetry"),
    "Emergency Communications": (0.10, True, "Independent emergency radio system"),
    "Habitat Lighting": (0.20, True, "Internal lights and essential work areas"),
    "Medical Equipment": (0.30, True, "Medical bay and life-monitoring equipment"),
    "Science Laboratory": (0.80, False, "Research instruments and sample analysis"),
    "ISRU Water Extraction": (1.80, False, "Pilot resource extraction and processing"),
    "Workshop Tools": (0.60, False, "Maintenance tools and fabrication equipment"),
    "Rover Charging": (1.50, False, "Recharge the surface exploration rover"),
    "Kitchen / Food Systems": (0.35, True, "Food preparation and cold storage"),
    "Recreation Systems": (0.25, False, "Optional comfort and recreation equipment"),
}

if "load_states" not in st.session_state:
    st.session_state.load_states = {k: v[1] for k, v in default_loads.items()}

# Read the latest widget states before drawing the scene, so the illustration
# and energy calculations update immediately when a switch is changed below.
load_kw = {}
for name, (rated, initial, description) in default_loads.items():
    on = st.session_state.get(f"toggle_{name}", st.session_state.load_states[name])
    load_kw[name] = rated if on else 0.0

total_load_kw = sum(load_kw.values())
daily_energy = total_load_kw * 24
night_days_design = st.slider(
    "Battery autonomy design target (days of darkness)",
    min_value=10.0, max_value=15.0, value=DAYS_AUTONOMY_DEFAULT, step=0.25,
    help="A lunar night is approximately 14 Earth days; 14.75 days is used as a conservative full half-cycle reference.",
)
reserve_soc = 1.0 - dod
usable_battery_energy = battery_nominal * dod * battery_eff
required_battery_nominal = (daily_energy * night_days_design) / max(dod * battery_eff, 0.01)

# PV must serve habitat daily demand AND recharge the energy used over the dark period
# during the following daylight period.
required_pv_energy_per_day = daily_energy + (daily_energy * night_days_design / LUNAR_DAY_DAYS)
pv_daily_energy = pv_kw * peak_sun_hours * derate
required_pv_kw = required_pv_energy_per_day / max(peak_sun_hours * derate, 0.01)
pv_margin = pv_daily_energy - required_pv_energy_per_day

# --------------------- BATTERY / NIGHT MODEL ------------------
# Simple state-of-charge estimate: during daylight, excess PV gradually charges
# from the minimum reserve to 100%; during lunar night, stored usable energy is
# consumed at the selected load rate. This is a planning visualization, not a
# detailed electrochemical or thermal battery model.
if daily_energy <= 0:
    soc = 100.0
    remaining_days = float("inf")
elif is_daylight:
    charge_surplus_per_day = max(pv_daily_energy - daily_energy, 0.0)
    target_charge_energy = battery_nominal * dod
    charge_progress = min(phase_elapsed / LUNAR_DAY_DAYS, 1.0)
    estimated_charged = min(target_charge_energy, charge_surplus_per_day * LUNAR_DAY_DAYS * charge_progress)
    soc = max(reserve_soc * 100, min(100.0, reserve_soc * 100 + estimated_charged / max(battery_nominal, 1) * 100))
    remaining_days = usable_battery_energy / daily_energy
else:
    # SOC falls according to the actual autonomy of the installed battery.
    night_progress = min(phase_elapsed / max(night_days_design, 0.01), 1.0)
    soc = max(reserve_soc * 100, 100.0 - (dod * 100 * night_progress))
    remaining_days = usable_battery_energy / daily_energy

# If PV is undersized, daylight charging may not reach full charge.
if is_daylight and daily_energy > 0:
    projected_end_soc = min(100.0, reserve_soc * 100 + max(pv_daily_energy - daily_energy, 0) * LUNAR_DAY_DAYS / max(battery_nominal, 1) * 100)
else:
    projected_end_soc = 100.0

# -------------------------- KPI ROW ---------------------------
st.markdown("---")
k1, k2, k3, k4 = st.columns(4)
k1.metric("LIVE LOAD", f"{total_load_kw:.2f} kW", f"{daily_energy:.1f} kWh / day")
k2.metric("BATTERY SOC", f"{soc:.1f}%", f"{battery_nominal:,.0f} kWh nominal")
k3.metric("PV GENERATION", f"{pv_daily_energy:,.0f} kWh/day", f"{pv_kw} kW installed")
k4.metric("NIGHT AUTONOMY", f"{remaining_days:.1f} days" if math.isfinite(remaining_days) else "No load", "At current load")

# ----------------------- SCENE SVG ----------------------------
# SVG is deliberately self-contained: no external images or assets required.
def make_scene(daylight: bool, soc_value: float, active_load_count: int, pv_power: int) -> str:
    sky_top = "#172b48" if daylight else "#050914"
    sky_bottom = "#26374b" if daylight else "#0a1020"
    sun_or_moon = (
        '<circle cx="1000" cy="112" r="43" fill="#f9d98b" opacity=".96"/>'
        '<circle cx="1000" cy="112" r="55" fill="#f9d98b" opacity=".10"/>'
        if daylight else
        '<circle cx="1000" cy="112" r="40" fill="#dce7f5" opacity=".92"/>'
        '<circle cx="985" cy="100" r="39" fill="#050914"/>'
    )
    stars = ""
    for i in range(58):
        x = (i * 173 + 37) % 1180
        y = (i * 79 + 19) % 270
        r = 1.0 + (i % 3) * .55
        stars += f'<circle cx="{x}" cy="{y}" r="{r}" fill="#e7f1ff" opacity="{0.35 + (i%5)*0.12:.2f}"/>'
    earth = """
      <circle cx="185" cy="112" r="35" fill="#287fbd"/>
      <path d="M159 98 Q175 78 190 88 L201 101 L193 112 L180 108 L171 125 L158 119 Z" fill="#66b987"/>
      <path d="M195 131 L207 122 L216 133 L204 145 L190 141 Z" fill="#77c58f"/>
      <ellipse cx="185" cy="112" rx="40" ry="39" fill="none" stroke="#a9dfff" stroke-width="3" opacity=".35"/>
      <text x="185" y="165" text-anchor="middle" fill="#d9eaff" font-size="13">EARTH</text>
    """
    terrain = """
      <path d="M0 385 Q80 360 155 381 Q240 350 320 382 Q420 342 520 377 Q620 352 720 382 Q820 347 920 378 Q1030 350 1180 380 L1180 620 L0 620 Z" fill="#8d8279"/>
      <path d="M0 430 Q130 393 230 427 Q340 391 450 430 Q590 395 700 428 Q820 398 940 432 Q1060 400 1180 425 L1180 620 L0 620 Z" fill="#625e5d"/>
      <path d="M0 488 Q140 450 260 488 Q400 450 540 488 Q680 455 820 490 Q980 452 1180 487 L1180 620 L0 620 Z" fill="#393d45"/>
      <g fill="#a9a09a" opacity=".55">
        <ellipse cx="90" cy="416" rx="24" ry="8"/><ellipse cx="370" cy="455" rx="35" ry="10"/>
        <ellipse cx="760" cy="423" rx="27" ry="8"/><ellipse cx="1080" cy="463" rx="42" ry="11"/>
      </g>
      <g fill="#292e36" opacity=".7">
        <circle cx="280" cy="500" r="3"/><circle cx="315" cy="480" r="5"/><circle cx="880" cy="490" r="4"/>
        <circle cx="930" cy="470" r="3"/><circle cx="1120" cy="510" r="5"/><circle cx="600" cy="520" r="4"/>
      </g>
      <g fill="none" stroke="#c4b9ae" stroke-width="2" opacity=".25">
        <path d="M40 458 Q85 445 130 458"/><path d="M470 474 Q530 455 585 474"/>
        <path d="M900 445 Q970 428 1030 446"/>
      </g>
    """
    # Habitat module cluster
    habitat = """
      <g stroke="#dce7f4" stroke-width="2">
        <rect x="440" y="294" width="205" height="88" rx="18" fill="#b7c4d2"/>
        <rect x="465" y="277" width="155" height="22" rx="8" fill="#e2eaf2"/>
        <rect x="485" y="319" width="48" height="35" rx="5" fill="#203d58"/>
        <rect x="545" y="319" width="48" height="35" rx="5" fill="#203d58"/>
        <rect x="610" y="326" width="22" height="40" rx="5" fill="#71879c"/>
        <rect x="386" y="326" width="54" height="48" rx="12" fill="#879aaa"/>
        <rect x="645" y="326" width="54" height="48" rx="12" fill="#879aaa"/>
        <rect x="395" y="339" width="45" height="20" rx="8" fill="#c5d2df"/>
        <rect x="645" y="339" width="45" height="20" rx="8" fill="#c5d2df"/>
        <path d="M440 340 L405 340 M645 340 L690 340" stroke="#e5edf5" stroke-width="7"/>
        <rect x="506" y="286" width="70" height="9" rx="4" fill="#71879c"/>
      </g>
      <g fill="#e7f2ff" font-size="12" font-weight="700">
        <text x="542" y="370" text-anchor="middle">LUNAR HABITAT</text>
      </g>
      <g fill="#f4d58b" opacity=".9"><circle cx="495" cy="336" r="4"/><circle cx="555" cy="336" r="4"/></g>
      <g stroke="#aab9c8" stroke-width="4" fill="none"><path d="M414 375 L414 394 L430 394"/><path d="M674 375 L674 394 L655 394"/></g>
    """
    # PV array with panel grid
    panels = ""
    for row in range(2):
        for col in range(6):
            x = 790 + col * 43
            y = 300 + row * 34
            panels += f'<rect x="{x}" y="{y}" width="38" height="27" rx="2" fill="#123b69" stroke="#72b9ed" stroke-width="1.2"/>'
            panels += f'<path d="M{x+12} {y} V{y+27} M{x+25} {y} V{y+27} M{x} {y+13} H{x+38}" stroke="#4d91c7" stroke-width=".8"/>'
    pv = f"""
      <g>
        <path d="M770 385 L1045 385" stroke="#aeb9c6" stroke-width="6"/>
        <path d="M795 385 L805 365 M1030 385 L1018 365" stroke="#b9c5d0" stroke-width="5"/>
        {panels}
        <path d="M785 296 L1050 296" stroke="#c3ced9" stroke-width="3"/>
        <text x="920" y="278" fill="#d9edff" font-size="14" text-anchor="middle" font-weight="700">SOLAR PV ARRAY · {pv_power} kW</text>
      </g>
    """
    battery = """
      <g>
        <rect x="710" y="350" width="54" height="42" rx="7" fill="#34485a" stroke="#c5d6e7" stroke-width="2"/>
        <rect x="720" y="358" width="34" height="25" rx="3" fill="#182838"/>
        <path d="M727 355 V350 H746 V355" stroke="#d5e2ed" stroke-width="3" fill="none"/>
        <text x="737" y="410" fill="#e6f0fb" font-size="11" text-anchor="middle">BESS</text>
      </g>
    """
    # Power cables, green when powered
    cable_color = "#55e0b0" if active_load_count else "#718096"
    cables = f"""
      <path d="M790 365 C745 410 710 410 690 370" fill="none" stroke="{cable_color}" stroke-width="4" stroke-dasharray="8 5"/>
      <path d="M710 370 C680 420 650 420 620 382" fill="none" stroke="{cable_color}" stroke-width="4" stroke-dasharray="8 5"/>
      <circle cx="710" cy="410" r="5" fill="{cable_color}"/>
      <text x="720" y="435" fill="#d7e5f3" font-size="11" text-anchor="middle">POWER BUS</text>
    """
    labels = """
      <text x="545" y="250" text-anchor="middle" fill="#d9eaff" font-size="13" font-weight="700">CREW & SCIENCE MODULES</text>
      <text x="920" y="440" text-anchor="middle" fill="#d9eaff" font-size="12">PHOTOVOLTAIC FIELD</text>
      <text x="100" y="570" fill="#e5e7eb" font-size="12" opacity=".7">LUNAR REGOLITH / SURFACE</text>
    """
    return f"""
    <svg viewBox="0 0 1180 620" width="100%" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Illustrated lunar base scene">
      <defs>
        <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{sky_top}"/><stop offset="1" stop-color="{sky_bottom}"/></linearGradient>
        <linearGradient id="ground" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#a49a90"/><stop offset="1" stop-color="#353a43"/></linearGradient>
        <filter id="glow"><feGaussianBlur stdDeviation="5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
      </defs>
      <rect width="1180" height="620" fill="url(#sky)"/>
      {stars}
      {earth}
      {sun_or_moon}
      <text x="1000" y="175" text-anchor="middle" fill="#dbeafe" font-size="12">{'SUN' if daylight else 'MOONLIT NIGHT'}</text>
      <path d="M0 385 Q80 360 155 381 Q240 350 320 382 Q420 342 520 377 Q620 352 720 382 Q820 347 920 378 Q1030 350 1180 380 L1180 620 L0 620 Z" fill="url(#ground)"/>
      {terrain}
      {habitat}
      {pv}
      {battery}
      {cables}
      {labels}
      <g transform="translate(35 30)">
        <rect width="205" height="62" rx="10" fill="#07111f" opacity=".72" stroke="#7794b5" stroke-opacity=".5"/>
        <text x="14" y="24" fill="#9fb8d4" font-size="11">LUNAR ENVIRONMENT</text>
        <text x="14" y="47" fill="#f5f8ff" font-size="18" font-weight="700">{'DAYLIGHT' if daylight else '14-DAY NIGHT MODE'}</text>
      </g>
      <g transform="translate(930 520)">
        <rect width="210" height="66" rx="10" fill="#07111f" opacity=".82" stroke="#7794b5" stroke-opacity=".5"/>
        <text x="12" y="22" fill="#9fb8d4" font-size="11">BATTERY STATE OF CHARGE</text>
        <rect x="12" y="34" width="184" height="13" rx="6" fill="#26384d"/>
        <rect x="12" y="34" width="{184*max(0,min(100,soc_value))/100:.1f}" height="13" rx="6" fill="#43d6a4"/>
        <text x="196" y="60" text-anchor="end" fill="#f4f8ff" font-size="12" font-weight="700">{soc_value:.0f}%</text>
      </g>
    </svg>
    """

scene = make_scene(is_daylight, soc, sum(1 for v in load_kw.values() if v > 0), pv_kw)
components.html(scene, height=640, scrolling=False)

phase_label = "Lunar daylight" if is_daylight else "Lunar night"
phase_color = "status-good" if is_daylight else "status-warn"
st.markdown(f'<div class="panel"><span class="{phase_color}">{phase}</span> · Lunar cycle day {lunar_day:.2f} / 29.5 · {phase_label} elapsed: {phase_elapsed:.2f} days</div>', unsafe_allow_html=True)

st.markdown("## ⚡ Electrical load management")
st.markdown("**Manual control:** أنت المتحكم الوحيد في كل مفتاح. البرنامج لا يفصل أي جهاز تلقائيًا حتى لو البطارية منخفضة؛ هو فقط يحسب الاستهلاك ويعرض التحذيرات، وأنت تقرر ما الذي تشغّله أو تفصله.")

# Master buttons are optional shortcuts; individual switches remain fully manual.
master_on, master_off, critical_btn, _ = st.columns([1, 1, 1.5, 2])
if master_on.button("⚡ Turn ALL ON", use_container_width=True):
    for name in default_loads:
        st.session_state[f"toggle_{name}"] = True
        st.session_state.load_states[name] = True
    st.rerun()
if master_off.button("⏻ Turn ALL OFF", use_container_width=True):
    for name in default_loads:
        st.session_state[f"toggle_{name}"] = False
        st.session_state.load_states[name] = False
    st.rerun()
if critical_btn.button("🛟 Critical systems only", use_container_width=True):
    critical_names = {
        "Oxygen Generation", "CO2 Removal System", "Water Recovery",
        "Thermal Control / Heaters", "Main Communications",
        "Emergency Communications", "Habitat Lighting", "Medical Equipment",
        "Kitchen / Food Systems"
    }
    for name in default_loads:
        state = name in critical_names
        st.session_state[f"toggle_{name}"] = state
        st.session_state.load_states[name] = state
    st.rerun()

load_cols = st.columns(3)
for i, (name, (rated, initial, description)) in enumerate(default_loads.items()):
    widget_key = f"toggle_{name}"
    if widget_key not in st.session_state:
        st.session_state[widget_key] = st.session_state.load_states.get(name, initial)
    with load_cols[i % 3]:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        on = st.toggle(name, key=widget_key)
        st.session_state.load_states[name] = on
        state_text = "🟢 ONLINE" if on else "🔴 OFFLINE"
        state_color = "status-good" if on else "status-warn"
        st.markdown(f'<div class="{state_color}">{state_text}</div>', unsafe_allow_html=True)
        st.markdown(f"**{rated:.2f} kW** rated")
        st.caption(description)
        st.markdown('</div>', unsafe_allow_html=True)

st.info("Battery condition never changes your switches automatically. If the battery reserve is insufficient, you will receive an alert and can manually switch off optional loads.")

# --------------------- DESIGN CALCULATIONS -------------------
st.markdown("## 🔋 Energy system sizing")
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("### Battery bank")
    st.metric("Required nominal capacity", f"{required_battery_nominal:,.0f} kWh")
    st.metric("Installed nominal capacity", f"{battery_nominal:,.0f} kWh")
    battery_ok = battery_nominal >= required_battery_nominal
    st.markdown(
        f'<p class="{"status-good" if battery_ok else "status-bad"}">{"✓ Battery capacity meets target" if battery_ok else "⚠ Battery capacity is undersized"}</p>',
        unsafe_allow_html=True,
    )
    st.caption(f"Usable energy after DoD and efficiency: {usable_battery_energy:,.0f} kWh")
with c2:
    st.markdown("### Solar array")
    st.metric("Required PV rating", f"{required_pv_kw:,.1f} kW")
    st.metric("Installed PV rating", f"{pv_kw:,.0f} kW")
    pv_ok = pv_kw >= required_pv_kw
    st.markdown(
        f'<p class="{"status-good" if pv_ok else "status-bad"}">{"✓ PV capacity meets recharge target" if pv_ok else "⚠ PV array is undersized"}</p>',
        unsafe_allow_html=True,
    )
    st.caption(f"Daily PV energy estimate: {pv_daily_energy:,.0f} kWh")
with c3:
    st.markdown("### Mission survival")
    if total_load_kw == 0:
        st.metric("Current load", "0 kW")
        st.markdown('<p class="status-good">All loads are offline. No electrical demand.</p>', unsafe_allow_html=True)
    else:
        st.metric("Battery autonomy", f"{remaining_days:.1f} days")
        survival_ok = remaining_days >= night_days_design
        st.markdown(
            f'<p class="{"status-good" if survival_ok else "status-bad"}">{"✓ Battery can cover design night" if survival_ok else "⚠ Battery cannot cover full design night"}</p>',
            unsafe_allow_html=True,
        )
    st.caption("Autonomy is estimated at the current selected load.")

st.markdown("---")
st.markdown("## 📊 Energy balance")
balance_col1, balance_col2 = st.columns([1, 1])
with balance_col1:
    st.markdown("**Daily demand by subsystem**")
    if total_load_kw > 0:
        for name, kw in load_kw.items():
            if kw > 0:
                st.write(f"{name}: **{kw:.2f} kW** · {kw*24:.1f} kWh/day")
                st.progress(min(1.0, kw / max(total_load_kw, 0.01)))
    else:
        st.info("All electrical loads are currently switched off.")
with balance_col2:
    st.markdown("**Power generation vs. required energy**")
    st.metric("PV daily energy", f"{pv_daily_energy:,.1f} kWh")
    st.metric("Energy needed for loads + battery recharge", f"{required_pv_energy_per_day:,.1f} kWh/day")
    st.metric("Daily energy margin", f"{pv_margin:+,.1f} kWh/day")
    if pv_margin >= 0:
        st.success("The selected PV array can theoretically serve the daily load and recharge the battery bank.")
    else:
        st.error("The selected PV array does not provide enough daily energy for the load and the planned recharge.")

# ----------------------- LOAD SHEDDING -----------------------
st.markdown("---")
st.markdown("## 🧠 Suggested manual load-shedding order")
st.write("هذه توصيات فقط وليست أوامر تلقائية. اختيار فصل أي حمل يظل بيدك من المفاتيح الموجودة بالأعلى.")
priority = [
    ("Life Support", "NEVER SHED during crew occupancy", "Critical"),
    ("Thermal Control", "Keep minimum safe habitat temperature", "Critical"),
    ("Communications", "Keep emergency and Earth communication available", "Critical"),
    ("Lighting", "Reduce to emergency / task lighting", "High"),
    ("Science Lab", "Pause non-essential experiments first", "Medium"),
    ("Workshop", "Turn off unless a repair is required", "Low"),
    ("ISRU Pilot Plant", "Pause during energy shortage unless mission-critical", "Low"),
    ("Recreation / Comfort", "Disable during survival power mode", "Low"),
]
for name, action, level in priority:
    cols = st.columns([1.5, 4, 1])
    cols[0].markdown(f"**{name}**")
    cols[1].write(action)
    cols[2].caption(level)

# -------------------------- WARNINGS --------------------------
st.markdown("---")
st.markdown("## 🚨 Mission alerts")
alerts = []
if not battery_ok:
    alerts.append("Battery bank is too small for the selected night-autonomy target.")
if not pv_ok:
    alerts.append("PV array is too small to serve the daily load and restore the battery during daylight.")
if total_load_kw > 0 and remaining_days < night_days_design and not is_daylight:
    alerts.append("Current battery autonomy is shorter than the selected lunar-night target.")
if load_kw.get("Oxygen Generation", 0) == 0 or load_kw.get("CO2 Removal System", 0) == 0:
    alerts.append("An atmosphere / life-support subsystem is OFF. This may become unsafe for an occupied habitat.")
if load_kw.get("Thermal Control / Heaters", 0) == 0:
    alerts.append("Thermal Control is OFF. Habitat temperature may become unsafe.")
if not alerts:
    st.success("No immediate design alerts. Continue monitoring energy reserve and critical loads.")
else:
    for a in alerts:
        st.warning(a)

# ----------------------- ASSUMPTIONS --------------------------
with st.expander("📘 Model assumptions & engineering notes"):
    st.markdown("""
    **Important:** This is an educational concept simulator, not a flight-qualified engineering design.

    - A lunar solar day/night half-cycle is approximated as **14.75 Earth days**.
    - PV daily energy = installed PV kW × equivalent full-sun hours × derating factor.
    - Daily demand = sum of selected electrical loads × 24 hours.
    - Battery nominal capacity = daily demand × autonomy days ÷ (DoD × discharge efficiency).
    - PV rating includes the energy needed to operate the habitat during daylight and recharge the energy used during the dark period.
    - Load ratings, solar hours, derating, battery efficiency and autonomy are user-adjustable assumptions.
    - Real lunar systems also need thermal management, radiation protection, dust mitigation, redundancy, power electronics, cabling losses, battery temperature limits, degradation, landing constraints and fault protection.
    - Some lunar sites have unusual illumination conditions. This model assumes a conventional long lunar night and does not model polar peaks of near-eternal light.
    """)

st.caption("MOONBASE: POWER SURVIVAL · Student concept prototype · Not an official NASA system or NASA-endorsed design")
