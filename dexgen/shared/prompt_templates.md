# Starsilk Consistency Bibles
These templates enforce the visual identity and lore of the Starsilk project.

## 1. The Character Bible (Character Lock)

The **Character Lock** is an immutable trait string that must be prepended to every generation prompt to ensure consistency across the distributed pipeline. 

### Core Character Traits
> "A cel-shaded small black-and-white dog, floppy ears down, human-like eyes, thick clean outlines, flat colors, consistent facial markings, no breed morphing."

**Assembly Strategy:**
`Final Prompt = [CHARACTER_LOCK], [STYLE_PRESET], [SCENE_PROMPT]`

---

## 2. Style Presets

Selectable styles that follow the Character Lock in the prompt assembly.

* **Cel-shaded:** "Cel-shaded animation style, striking visual contrast."
* **Flat Animation:** "Flat 2D animation style, vector art, smooth curves."
* **Glow:** "Ethereal glowing emission effect, dark background contrast."
* **None:** "" (Empty string)

---

## 3. Negative Prompt Master

The Global Kill-List. This string must be prepended to the negative prompt field for *every* generation on the remote node to prevent the model from hallucinating photorealism or unwanted artifacts.

> "blurry, distorted, low quality, gradient backgrounds, realistic textures, 3D render, over-detailed, inconsistent line weight."
