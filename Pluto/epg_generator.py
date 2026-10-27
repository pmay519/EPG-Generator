#!/usr/bin/env python3
from datetime import datetime
import glob
import json
import os
import re
import urllib.request
import xml.etree.ElementTree as ET


def parse_m3u(filepath):
  """Parses local M3U file to extract tvg-id, tvg-name, and display names."""
  channels = []
  if not os.path.exists(filepath):
    return channels

  with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
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

        tvg_id = attributes.get("tvg-id", "").strip()
        tvg_name = attributes.get("tvg-name", "").strip()
        tvg_logo = attributes.get("tvg-logo", "").strip()
        clean_name = display_name.strip()

        if not tvg_id:
          tvg_id = clean_name.lower().replace(" ", ".")

        channels.append({
            "tvg-id": tvg_id,
            "tvg-name": tvg_name or clean_name,
            "tvg-logo": tvg_logo,
            "display-name": clean_name,
        })
  return channels


def fetch_pluto_guide():
  url = "https://api.pluto.tv/v2/channels.json"
  req = urllib.request.Request(
      url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
  )
  try:
    with urllib.request.urlopen(req) as response:
      return json.loads(response.read().decode("utf-8"))
  except Exception as e:
    print(f"Error fetching Pluto guide API: {e}")
    return []


def generate_xmltv():
  m3u_files = glob.glob("*.m3u")
  if not m3u_files:
    print("No M3U playlist file found in the Pluto folder.")
    return

  playlist_channels = parse_m3u(m3u_files[0])
  print(f"Loaded {len(playlist_channels)} channels from local playlist.")

  api_channels = fetch_pluto_guide()
  if not api_channels:
    print("No channel data retrieved from Pluto API.")
    return

  # Map API channels by name and slug for easy matching
  api_map = {}
  for ch in api_channels:
    name = ch.get("name", "").strip().lower()
    slug = ch.get("slug", "").strip().lower()
    if name:
      api_map[name] = ch
    if slug:
      api_map[slug] = ch

  root = ET.Element("tv")
  root.set("generator-info-name", "Pluto-Real-EPG-Generator")

  matched_count = 0
  for pch in playlist_channels:
    tvg_id = pch["tvg-id"]
    display_name = pch["display-name"].strip().lower()
    tvg_name = pch["tvg-name"].strip().lower()

    # Find corresponding Pluto API channel
    api_ch = (
        api_map.get(display_name)
        or api_map.get(tvg_name)
        or api_map.get(display_name.replace(" ", "-"))
    )

    # Write channel element using local playlist's exact tvg-id
    channel_elem = ET.SubElement(root, "channel", id=tvg_id)
    name_elem = ET.SubElement(channel_elem, "display-name")
    name_elem.text = pch["display-name"]

    if pch["tvg-logo"]:
      icon_elem = ET.SubElement(channel_elem, "icon")
      icon_elem.set("src", pch["tvg-logo"])

    if api_ch:
      matched_count += 1
      timelines = api_ch.get("timelines", [])
      for slot in timelines:
        title = slot.get("title", "Live Broadcast")
        desc = slot.get("description", "No description available.")
        start_str = slot.get("start")
        stop_str = slot.get("stop")

        if not start_str or not stop_str:
          continue

        try:
          start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
          stop_dt = datetime.fromisoformat(stop_str.replace("Z", "+00:00"))

          prog_elem = ET.SubElement(root, "programme")
          prog_elem.set("channel", tvg_id)
          prog_elem.set("start", start_dt.strftime("%Y%m%d%H%M%S %z"))
          prog_elem.set("stop", stop_dt.strftime("%Y%m%d%H%M%S %z"))

          title_elem = ET.SubElement(prog_elem, "title")
          title_elem.set("lang", "en")
          title_elem.text = title

          desc_elem = ET.SubElement(prog_elem, "desc")
          desc_elem.set("lang", "en")
          desc_elem.text = desc
        except Exception:
          continue

  tree = ET.ElementTree(root)
  with open("epg.xml", "wb") as f:
    f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
    tree.write(f, encoding="utf-8", xml_declaration=False)

  print(
      f"Successfully generated EPG. Matched {matched_count} out of"
      f" {len(playlist_channels)} playlist channels."
  )


if __name__ == "__main__":
  generate_xmltv()