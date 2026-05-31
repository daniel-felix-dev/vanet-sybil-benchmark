"""Generate one sumo .cfg for each sybil rate scenario."""
import os

SUMO_DIR = os.path.dirname(__file__)
RATES = [10, 20, 30, 40]

TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <input>
    <net-file value="network.net.xml"/>
    <route-files value="routes_sybil{rate}.rou.xml"/>
  </input>
  <time>
    <begin value="0"/>
    <end value="500"/>
    <step-length value="1"/>
  </time>
  <report>
    <no-step-log value="true"/>
    <no-warnings value="true"/>
  </report>
</configuration>
"""

for r in RATES:
    path = os.path.join(SUMO_DIR, f"scenario_sybil{r}.sumocfg")
    with open(path, "w") as f:
        f.write(TEMPLATE.format(rate=r))
    print(f"Written: {path}")
