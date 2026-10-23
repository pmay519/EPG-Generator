#!/usr/bin/env python3
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

# Replace with your actual M3U playlist URL or local file path
M3U_URL = "samsungtvplus_all.m3u"
OUTPUT_XML = "epg.xml"


def parse_m3u(url_or_path):
  """Parses an M3U playlist and extracts channel details."""
  channels = []

  if url_or_path.startswith("http://") or url_or_path.startswith("https://"):
    req = urllib.request.Request(
        url_or_path, headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req) as response:
      content = response.read().decode("utf-8", errors="ignore")
    lines = content.splitlines()
  else:
    with open(url_or_path, "r", encoding="utf-8", errors="ignore") as f:
      lines = f.readlines()

  extinf_pattern = re.compile(r"#EXTINF:(.*?),(.*)$")
  attr_pattern = re.compile(r'([A-Za-z0-9_-]+)=["\']([^"\']*)["\']')

  for line in lines:
    line = line.strip()
    if line.startswith("#EXTINF:"):
      match = extinf_pattern.match(line)
      if match:
        attributes_str, display_name = match.groups()
        attributes = dict(attr_pattern.findall(attributes_str))

        channel_info = {
            "tvg-id": attributes.get("tvg-id", "").strip(),
            "tvg-name": attributes.get("tvg-name", "").strip(),
            "tvg-logo": attributes.get("tvg-logo", "").strip(),
            "group-title": attributes.get("group-title", "").strip(),
            "display-name": display_name.strip(),
        }

        # Fallback identifier if tvg-id is missing in the M3U
        if not channel_info["tvg-id"]:
          channel_info["tvg-id"] = (
              channel_info["display-name"].lower().replace(" ", ".")
          )

        channels.append(channel_info)

  return channels


def generate_xmltv(channels, output_filename):
  """Generates an XMLTV structured file for every channel found."""
  root = ET.Element("tv")
  root.set("generator-info-name", "M3U-EPG-Generator")

  # Add channel definitions
  for ch in channels:
    channel_elem = ET.SubElement(root, "channel")
    channel_elem.set("id", ch["tvg-id"])

    name_elem = ET.SubElement(channel_elem, "display-name")
    name_elem.text = ch["display-name"]

    if ch["tvg-logo"]:
      icon_elem = ET.SubElement(channel_elem, "icon")
      icon_elem.set("src", ch["tvg-logo"])

  # Generate 24 hours of rolling program blocks to prevent empty grids
  now = datetime.utcnow()
  start_time = now.replace(minute=0, second=0, microsecond=0)

  for ch in channels:
    for i in range(24):
      prog_start = start_time + timedelta(hours=i)
      prog_stop = prog_start + timedelta(hours=1)

      prog_elem = ET.SubElement(root, "programme")
      prog_elem.set("channel", ch["tvg-id"])
      prog_elem.set("start", prog_start.strftime("%Y%m%d%H%M%S +0000"))
      prog_elem.set("stop", prog_stop.strftime("%Y%m%d%H%M%S +0000"))

      title_elem = ET.SubElement(prog_elem, "title")
      title_elem.set("lang", "en")
      title_elem.text = f"Live Broadcast - {ch['display-name']}"

      desc_elem = ET.SubElement(prog_elem, "desc")
      desc_elem.set("lang", "en")
      desc_elem.text = "Automated daily EPG entry generated from M3U metadata."

  tree = ET.ElementTree(root)
  with open(output_filename, "wb") as f:
    f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
    tree.write(f, encoding="utf-8", xml_declaration=False)

  print(
      f"Successfully created EPG for {len(channels)} channels ->"
      f" {output_filename}"
  )


if __name__ == "__main__":
  print("Processing M3U file...")
  channel_list = parse_m3u(M3U_URL)
  print(f"Discovered {len(channel_list)} channels.")
  generate_xmltv(channel_list, OUTPUT_XML)