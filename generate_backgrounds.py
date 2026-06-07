"""
Valdenmoor Arka Plan Üretici — Vertex AI Imagen
Kullanım:
  pip install google-cloud-aiplatform pillow python-dotenv
  python generate_backgrounds.py
  python generate_backgrounds.py --only throne_room
"""

import argparse
import os
import time
from pathlib import Path
from dotenv import load_dotenv

script_dir = Path(__file__).parent
for env_path in [script_dir / ".env", script_dir / "backend" / ".env", script_dir.parent / ".env"]:
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ .env yüklendi: {env_path}")
        break

PROJECT_ID = os.getenv("VERTEX_AI_PROJECT_ID")
_env_location = os.getenv("VERTEX_AI_LOCATION", "us-central1")
LOCATION = "us-central1" if _env_location == "global" else _env_location

LOCATIONS = {
    "throne_room": "Medieval fantasy throne room, grand stone hall, tall gothic windows with colored light, large ornate throne on raised platform, royal banners hanging from ceiling, flickering torches on walls, dusty beams of light, majestic and imposing atmosphere",
    "great_hall": "Medieval castle great hall, long wooden feasting tables, roaring fireplace at far end, antler chandeliers with candles, stone walls with tapestries and hunting trophies, warm golden light, noble gathering atmosphere",
    "war_room": "Medieval war room, large wooden table with detailed map of kingdom, candles dripping wax, quill and parchment, mounted swords and shields on walls, dark stone walls, tense strategic atmosphere",
    "castle_corridor": "Medieval castle corridor at night, stone walls with torch sconces casting orange glow, suits of armor standing guard, narrow arrow slit windows showing moonlit courtyard, shadows and mystery",
    "castle_exterior": "Valdenmoor castle exterior at dusk, imposing stone fortress on hilltop, banners flying in wind, village and farmland below, dramatic cloudy sky with orange sunset, epic fantasy atmosphere",
    "ashenmoor_market": "Medieval fantasy market square, busy cobblestone plaza, merchant stalls with colorful awnings, timber framed buildings, crowd of people trading, castle walls visible in background, daytime bustling atmosphere",
    "ashenmoor_streets": "Medieval fantasy city street at night, narrow cobblestone alley, timber framed houses leaning close, hanging lanterns casting warm glow, puddles reflecting light, mysterious and atmospheric",
    "dawnhold_fortress": "Northern border fortress in fantasy setting, dark stone walls on mountain pass, snow dusted battlements, cold grey sky, northern pine forest beyond walls, guards patrolling, cold and foreboding atmosphere",
    "varethis_harbor": "Medieval fantasy harbor city, wooden docks with tall masted ships, bustling port market, stone warehouses, seagulls, blue sea stretching to horizon, warm southern light",
    "varethis_sea": "Fantasy Mediterranean harbor at golden hour, calm blue sea, stone lighthouse, fishing boats and merchant vessels, warm orange sky, peaceful and prosperous atmosphere",
    "throne_antechamber": "Medieval castle antechamber, stone arched waiting room, wooden benches, royal guards standing at attention, heavy wooden doors leading to throne room, dim torch light, formal and tense",
    "castle_dungeon": "Medieval castle dungeon, dark stone cell corridor, iron barred doors, dripping water, single torch barely illuminating, chains on walls, cold and oppressive atmosphere",
    "castle_battlements": "Medieval castle battlements at night, stone crenellations, archer slits, view over dark kingdom below with village lights, full moon and stars, cold wind, lone guard silhouette",
    "royal_chambers": "Medieval royal bedchamber, large four poster bed with rich curtains, stone walls with tapestries, fireplace with dying embers, moonlight through tall narrow window, private and quiet atmosphere",
    "forest_path": "Dark medieval fantasy forest path, ancient gnarled trees forming canopy, dappled light filtering through, mist at ground level, mysterious and slightly ominous atmosphere, no characters",
    "selmara_palace": "Eastern medieval fantasy palace exterior, golden domed architecture, lush courtyard gardens, marble columns, warm afternoon light, prosperous and elegant atmosphere",
    "kadir_bazaar": "Arabian fantasy bazaar, colorful silk tents and awnings, exotic spices and goods, oil lanterns, desert architecture with arches and tiles, warm golden light, bustling and mysterious",
    "battlefield": "Epic medieval fantasy battlefield aftermath, torn banners in mud, abandoned weapons, smoldering fires, dramatic stormy sky, ravens circling, desolate and somber atmosphere",
    "council_chamber": "Medieval castle council chamber, round stone table with carved chairs, tall windows, royal seals on walls, maps and scrolls, candelabras, formal atmosphere for political meetings",
    "chapel": "Medieval castle chapel interior, simple stone nave, rows of wooden pews, tall narrow windows with colored glass, altar with candles, incense smoke, peaceful and sacred atmosphere",
    "onboarding_bg": "Valdenmoor medieval fantasy kingdom panoramic vista, vast kingdom stretching to horizon, imposing dark stone castle on hilltop in foreground, winding river through valley below, distant mountains with snow caps, dramatic golden sunset with deep purple and orange clouds, rays of light breaking through storm clouds illuminating the castle battlements, epic and majestic atmosphere, sense of power and destiny, wide cinematic composition, no characters, no people, no text",
}

STYLE_PREFIX = (
    "Dark fantasy oil painting style, detailed architectural background, "
    "cinematic lighting, no characters, no people, no text, no watermark, no logo, "
    "medieval fantasy setting, dramatic atmosphere, "
)

MODELS_TO_TRY = [
    "imagen-3.0-generate-002",
    "imagen-3.0-generate-001",
    "imagegeneration@006",
    "imagegeneration@005",
]

def generate_image(project_id, location, location_key, prompt, output_dir):
    output_path = output_dir / f"{location_key}.png"

    if output_path.exists():
        print(f"  ⏭ Zaten var, atlandı: {location_key}.png")
        return True

    import vertexai
    from vertexai.preview.vision_models import ImageGenerationModel
    vertexai.init(project=project_id, location=location)

    full_prompt = STYLE_PREFIX + prompt

    for model_name in MODELS_TO_TRY:
        try:
            model = ImageGenerationModel.from_pretrained(model_name)
            response = model.generate_images(
                prompt=full_prompt,
                number_of_images=1,
                aspect_ratio="16:9",
            )
            if response.images:
                response.images[0].save(str(output_path))
                print(f"  ✅ Kaydedildi: {location_key}.png ({model_name})")
                return True
        except Exception as e:
            print(f"  ⚠ {model_name}: {e}")
            continue

    print(f"  ❌ Tüm modeller başarısız: {location_key}")
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="./frontend/assets/backgrounds")
    parser.add_argument("--only", default=None)
    parser.add_argument("--delay", type=float, default=3.0)
    args = parser.parse_args()

    if not PROJECT_ID:
        print("❌ VERTEX_AI_PROJECT_ID .env'de bulunamadı!")
        return

    print(f"\n🏰 Valdenmoor Arka Plan Üretici — Vertex AI Imagen")
    print(f"📋 Project: {PROJECT_ID} | Location: {LOCATION}")

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 Çıktı: {output_dir.absolute()}")

    locations = LOCATIONS
    if args.only:
        if args.only not in LOCATIONS:
            print(f"❌ Bilinmeyen mekan: {args.only}")
            print(f"Mevcut mekanlar: {', '.join(LOCATIONS.keys())}")
            return
        locations = {args.only: LOCATIONS[args.only]}

    print(f"🖼  Toplam mekan: {len(locations)}\n")

    success = 0
    fail = 0

    for i, (key, prompt) in enumerate(locations.items(), 1):
        print(f"[{i}/{len(locations)}] {key}")
        ok = generate_image(PROJECT_ID, LOCATION, key, prompt, output_dir)
        if ok:
            success += 1
        else:
            fail += 1
        if i < len(locations):
            time.sleep(args.delay)

    print(f"\n✅ Başarılı: {success} | ❌ Başarısız: {fail}")
    print(f"📁 Görseller: {output_dir.absolute()}")

if __name__ == "__main__":
    main()
