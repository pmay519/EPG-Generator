#!/usr/bin/env python3
from datetime import datetime, timezone
import json
import urllib.request
import xml.etree.ElementTree as ET


def fetch_pluto_guide():
  url = "https://api.pluto.tv/v2/channels"
  req = urllib.request.Request(
      url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
  )
  try:
    with urllib.request.urlopen(req) as response:
      return json.loads(response.read().decode("utf-8"))
  except Exception as e:
    print(f"Error fetching Pluto guide API: {e}")
    return []


def generate_pluto_xmltv():
  channels_data = fetch_pluto_guide()
  if not channels_data:
    print("No channel data retrieved from Pluto API.")
    return

  root = ET.Element("tv")
  root.set("generator-info-name", "Pluto-Real-EPG-Generator")

  for channel in channels_data:
    chan_id = str(channel.get("_id", ""))
    chan_name = channel.get("name", "Unknown Channel")
    logo_path = channel.get("colorLogoPNG", {}).get("path", "")

    # Create channel element
    channel_elem = ET.SubElement(root, "channel", id=chan_id)
    display_name = ET.SubElement(channel_elem, "display-name")
    display_name.text = chan_name

    if logo_path:
      icon_elem = ET.SubElement(channel_elem, "icon")
      icon_elem.set("src", logo_path)

    # Process actual show timelines from Pluto API
    timelines = channel.get("timelines", [])
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

        start_formatted = start_dt.strftime("%Y%m%d%H%M%S %z")
        stop_formatted = stop_dt.strftime("%Y%m%d%H%M%S %z")

        prog_elem = ET.SubElement(root, "programme")
        prog_elem.set("channel", chan_id)
        prog_elem.set("start", start_formatted)
        prog_elem.set("stop", stop_formatted)

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

  print(f"Successfully generated real EPG data for {len(channels_data)} channels.")


if __name__ == "__main__":
  generate_pluto_xmltv()