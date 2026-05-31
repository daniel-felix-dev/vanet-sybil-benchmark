"""
Generate valid SUMO route files for the benchmark.
Uses randomTrips.py → duarouter for legitimate vehicles.
Sybil vehicles are added as clones sharing an attacker's origin edge.
"""
import os, sys, subprocess, random
import xml.etree.ElementTree as ET
import sumolib

SUMO_HOME = r"C:\Program Files (x86)\Eclipse\Sumo"
SUMO_BIN  = os.path.join(SUMO_HOME, "bin")
TOOLS     = os.path.join(SUMO_HOME, "tools")
SIM_DIR   = os.path.dirname(os.path.abspath(__file__))
NET_FILE  = os.path.join(SIM_DIR, "network.net.xml")

N_LEGIT      = 80
N_ATTACKERS  = 5
SYBIL_RATES  = [10, 20, 30, 40]
SIM_END      = 500
SEED         = 42


def run(cmd, check=True):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"Command failed:\n{r.stderr[:800]}")
    return r.returncode == 0


def build_route_from_edge(net, start_edge_id, rng, length=4):
    """Follow random outgoing edges without revisiting to build a valid route."""
    route = [start_edge_id]
    visited = {start_edge_id}
    cur = net.getEdge(start_edge_id)
    for _ in range(length - 1):
        outs = [e for e in cur.getOutgoing().keys() if e.getID() not in visited]
        if not outs:
            break
        cur = rng.choice(outs)
        route.append(cur.getID())
        visited.add(cur.getID())
    return route


def generate_for_rate(rate_pct):
    rng = random.Random(SEED + rate_pct)
    net = sumolib.net.readNet(NET_FILE)
    all_edges = [e for e in net.getEdges() if not e.getID().startswith(":")]

    n_sybil = int(round(N_LEGIT * rate_pct / (100 - rate_pct)))
    n_per_attacker = max(1, n_sybil // N_ATTACKERS)

    # ── Step 1: randomTrips for legitimate vehicles ────────────────────────────
    trips_xml  = os.path.join(SIM_DIR, f"_tmp_trips{rate_pct}.xml")
    routes_xml = os.path.join(SIM_DIR, f"_tmp_routes{rate_pct}.rou.xml")

    run([
        sys.executable,
        os.path.join(TOOLS, "randomTrips.py"),
        "-n", NET_FILE,
        "-o", trips_xml,
        "-b", "0", "-e", str(SIM_END),
        "--prefix", "legit_",
        "--period", str(max(1, SIM_END // N_LEGIT)),
        "--seed", str(SEED),
        "--min-distance", "200",
    ])

    run([
        os.path.join(SUMO_BIN, "duarouter.exe"),
        "-n", NET_FILE,
        "-t", trips_xml,
        "-o", routes_xml,
        "--ignore-errors", "--no-warnings",
    ])

    # ── Step 2: Parse duarouter output ────────────────────────────────────────
    tree = ET.parse(routes_xml)
    root_in = tree.getroot()

    # duarouter writes either <vehicle><route .../></vehicle>
    # or top-level <route/> + <vehicle/>. Collect all edges per vehicle id.
    route_edges = {}   # vid -> edges string
    for el in root_in.iter("vehicle"):
        vid = el.get("id")
        r_el = el.find("route")
        if r_el is not None:
            route_edges[vid] = r_el.get("edges", "")
    # Also handle top-level <route> with id = routeN pattern
    top_routes = {}
    for el in root_in.iter("route"):
        if el.get("id"):
            top_routes[el.get("id")] = el.get("edges", "")

    # ── Step 3: Build combined output file ────────────────────────────────────
    root = ET.Element("routes")

    vt = ET.SubElement(root, "vType")
    vt.set("id", "legitimate"); vt.set("color", "0,0,255")
    vt.set("accel", "2.6"); vt.set("decel", "4.5"); vt.set("maxSpeed", "13.89")

    vs = ET.SubElement(root, "vType")
    vs.set("id", "sybil"); vs.set("color", "255,0,0")
    vs.set("accel", "2.6"); vs.set("decel", "4.5"); vs.set("maxSpeed", "13.89")

    # Copy all legitimate elements (preserve ordering)
    for el in root_in:
        new = ET.SubElement(root, el.tag)
        new.attrib.update(el.attrib)
        if el.tag == "vehicle":
            new.set("type", "legitimate")
            for child in el:
                c = ET.SubElement(new, child.tag)
                c.attrib.update(child.attrib)

    # ── Step 4: Add Sybil vehicles ────────────────────────────────────────────
    sybil_count = 0
    for atk in range(N_ATTACKERS):
        # Pick a random start edge for this attacker
        start_edge = rng.choice(all_edges)
        route = build_route_from_edge(net, start_edge.getID(), rng, length=5)
        depart_t = str(rng.randint(0, 50))

        for _ in range(n_per_attacker):
            vid = f"sybil_{sybil_count}"
            v_el = ET.SubElement(root, "vehicle")
            v_el.set("id", vid)
            v_el.set("type", "sybil")
            v_el.set("depart", depart_t)
            v_el.set("departPos", str(round(rng.uniform(0, 5), 1)))
            r_el = ET.SubElement(v_el, "route")
            r_el.set("edges", " ".join(route))
            sybil_count += 1

    # Sort all vehicle children by depart time (SUMO requires this)
    vehicles_out = [(el, float(el.get("depart", 0)))
                    for el in root if el.tag == "vehicle"]
    non_vehicles = [el for el in root if el.tag != "vehicle"]

    root_sorted = ET.Element("routes")
    for el in non_vehicles:
        root_sorted.append(el)
    for el, _ in sorted(vehicles_out, key=lambda x: x[1]):
        root_sorted.append(el)

    # Write
    out_path = os.path.join(SIM_DIR, f"routes_sybil{rate_pct}.rou.xml")
    ET.indent(ET.ElementTree(root_sorted), space="  ")
    ET.ElementTree(root_sorted).write(out_path, encoding="unicode", xml_declaration=True)

    # Cleanup
    for f in [trips_xml, routes_xml,
              routes_xml.replace(".rou.xml", ".rou.alt.xml")]:
        try: os.remove(f)
        except: pass

    print(f"  sybil{rate_pct}%: legit={N_LEGIT}, sybil_ids={sybil_count} -> {os.path.basename(out_path)}")


if __name__ == "__main__":
    rates = [int(a) for a in sys.argv[1:]] if len(sys.argv) > 1 else SYBIL_RATES
    for r in rates:
        print(f"Generating routes sybil{r}%...")
        generate_for_rate(r)
    print("Done.")
