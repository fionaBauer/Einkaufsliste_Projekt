"""Eingebautes Lebensmittel-Wörterbuch.

Wird mit `python manage.py seed_ingredients` eingespielt (läuft auch bei jedem Deploy).
Es werden nur fehlende Einträge angelegt – vorhandene Zutaten (auch mit anderer
Groß-/Kleinschreibung) bleiben unverändert, inklusive ihrer Kategorie.

Format: Kategorie -> Liste von "Name:Einheit". Einheiten: g, kg, ml, l, pcs, pkg, el, tl.
Neue Einträge einfach in der passenden Liste ergänzen.
"""
from .models import IngredientCategory as C

SEED_INGREDIENTS = {
    C.FRUIT_VEG: [
        "Apfel:pcs", "Banane:pcs", "Birne:pcs", "Orange:pcs", "Mandarine:pcs", "Zitrone:pcs",
        "Limette:pcs", "Grapefruit:pcs", "Weintrauben:g", "Erdbeeren:g", "Himbeeren:g",
        "Heidelbeeren:g", "Kiwi:pcs", "Mango:pcs", "Ananas:pcs", "Wassermelone:pcs",
        "Honigmelone:pcs", "Pfirsich:pcs", "Nektarine:pcs", "Pflaumen:g", "Kirschen:g",
        "Avocado:pcs", "Granatapfel:pcs", "Tomate:pcs", "Cherrytomaten:g", "Gurke:pcs",
        "Paprika:pcs", "Zwiebel:pcs", "Rote Zwiebel:pcs", "Frühlingszwiebel:pcs",
        "Knoblauch:pcs", "Karotte:pcs", "Kartoffel:kg", "Süßkartoffel:pcs", "Zucchini:pcs",
        "Aubergine:pcs", "Brokkoli:pcs", "Blumenkohl:pcs", "Spinat:g", "Rucola:g",
        "Eisbergsalat:pcs", "Feldsalat:g", "Kopfsalat:pcs", "Champignons:g", "Lauch:pcs",
        "Sellerie:pcs", "Staudensellerie:pcs", "Weißkohl:pcs", "Rotkohl:pcs", "Rosenkohl:g",
        "Kohlrabi:pcs", "Grüne Bohnen:g", "Erbsen:g", "Mais:pcs", "Kürbis:pcs",
        "Rote Bete:g", "Radieschen:pcs", "Ingwer:g", "Chili:pcs", "Petersilie:pcs",
        "Basilikum:pcs", "Schnittlauch:pcs", "Koriander:pcs", "Dill:pcs", "Minze:pcs",
        "Spargel:g", "Fenchel:pcs", "Pak Choi:pcs",
    ],
    C.BREAD: [
        "Brot:pcs", "Vollkornbrot:pcs", "Toastbrot:pkg", "Brötchen:pcs", "Baguette:pcs",
        "Ciabatta:pcs", "Laugenbrezel:pcs", "Croissant:pcs", "Tortilla-Wraps:pkg",
        "Pita:pcs", "Fladenbrot:pcs", "Knäckebrot:pkg", "Bagel:pcs", "Burger-Brötchen:pkg",
    ],
    C.MEAT_FISH: [
        "Hähnchenbrustfilet:g", "Hähnchenschenkel:g", "Putenbrust:g", "Rinderhackfleisch:g",
        "Gemischtes Hackfleisch:g", "Rindersteak:g", "Schweinefilet:g", "Schnitzel:g",
        "Bacon:g", "Speckwürfel:g", "Kochschinken:g", "Salami:g", "Würstchen:pcs",
        "Bratwurst:pcs", "Chorizo:g", "Lachsfilet:g", "Räucherlachs:g", "Thunfisch:g",
        "Garnelen:g", "Kabeljau:g", "Forelle:g", "Lammfleisch:g", "Gyros:g",
    ],
    C.DAIRY: [
        "Milch:l", "Hafermilch:l", "Butter:g", "Sahne:ml", "Schmand:g", "Saure Sahne:g",
        "Crème fraîche:g", "Joghurt:g", "Griechischer Joghurt:g", "Skyr:g", "Quark:g",
        "Frischkäse:g", "Mozzarella:g", "Parmesan:g", "Gouda:g", "Emmentaler:g",
        "Feta:g", "Halloumi:g", "Mascarpone:g", "Ricotta:g", "Cheddar:g",
        "Geriebener Käse:g", "Eier:pcs", "Buttermilch:ml",
    ],
    C.GRAINS: [
        "Spaghetti:g", "Penne:g", "Fusilli:g", "Tagliatelle:g", "Lasagneplatten:g",
        "Nudeln:g", "Gnocchi:g", "Reis:g", "Basmatireis:g", "Jasminreis:g", "Risottoreis:g",
        "Couscous:g", "Bulgur:g", "Quinoa:g", "Haferflocken:g", "Müsli:g", "Cornflakes:g",
        "Polenta:g", "Glasnudeln:g", "Mie-Nudeln:g",
    ],
    C.CANNED: [
        "Gehackte Tomaten:g", "Passierte Tomaten:g", "Tomatenmark:g", "Kokosmilch:ml",
        "Kidneybohnen:g", "Kichererbsen:g", "Linsen:g", "Rote Linsen:g", "Weiße Bohnen:g",
        "Mais (Dose):g", "Thunfisch (Dose):g", "Oliven:g", "Gewürzgurken:g", "Kapern:g",
        "Ananas (Dose):g",
    ],
    C.SPICES: [
        "Salz:g", "Pfeffer:g", "Paprikapulver:tl", "Currypulver:tl", "Kreuzkümmel:tl",
        "Zimt:tl", "Oregano:tl", "Thymian:tl", "Rosmarin:tl", "Muskatnuss:tl",
        "Kurkuma:tl", "Chiliflocken:tl", "Garam Masala:tl", "Knoblauchpulver:tl",
        "Lorbeerblätter:pcs", "Gemüsebrühe:ml", "Hühnerbrühe:ml", "Olivenöl:el",
        "Rapsöl:el", "Sonnenblumenöl:el", "Sesamöl:el", "Balsamico:el", "Essig:el",
        "Sojasauce:el", "Ketchup:el", "Senf:tl", "Mayonnaise:el", "Pesto:g",
        "Currypaste:el", "Sriracha:tl", "Worcestershiresauce:tl", "Tahini:el",
    ],
    C.BAKING: [
        "Mehl:g", "Vollkornmehl:g", "Zucker:g", "Brauner Zucker:g", "Puderzucker:g",
        "Vanillezucker:pkg", "Backpulver:pkg", "Natron:tl", "Hefe:pkg", "Trockenhefe:pkg",
        "Speisestärke:el", "Kakaopulver:el", "Honig:el", "Ahornsirup:el", "Schokodrops:g",
        "Gemahlene Mandeln:g", "Kokosraspeln:g", "Gelatine:pkg",
    ],
    C.SNACKS: [
        "Schokolade:pcs", "Chips:pkg", "Kekse:pkg", "Gummibärchen:pkg", "Nüsse:g",
        "Mandeln:g", "Walnüsse:g", "Cashewkerne:g", "Erdnüsse:g", "Erdnussbutter:g",
        "Nuss-Nougat-Creme:g", "Müsliriegel:pcs", "Popcorn:pkg", "Salzstangen:pkg",
        "Marmelade:g",
    ],
    C.FREEZER: [
        "TK-Erbsen:g", "TK-Spinat:g", "TK-Beeren:g", "TK-Gemüsemischung:g", "Pommes:g",
        "TK-Pizza:pcs", "Fischstäbchen:pkg", "Speiseeis:pkg", "TK-Kräuter:pkg",
    ],
    C.DRINKS: [
        "Wasser:l", "Mineralwasser:l", "Apfelsaft:l", "Orangensaft:l", "Cola:l",
        "Limonade:l", "Eistee:l", "Kaffee:g", "Kaffeebohnen:g", "Tee:pkg", "Grüner Tee:pkg",
        "Bier:pcs", "Weißwein:ml", "Rotwein:ml",
    ],
    C.OTHER: [
        "Küchenrolle:pkg", "Toilettenpapier:pkg", "Spülmittel:pcs", "Müllbeutel:pkg",
        "Alufolie:pcs", "Frischhaltefolie:pcs", "Backpapier:pcs",
    ],
}


def iter_seed_ingredients():
    """Liefert (name, kategorie, einheit) für alle Einträge."""
    for category, entries in SEED_INGREDIENTS.items():
        for entry in entries:
            name, unit = entry.rsplit(":", 1)
            yield name, category, unit
