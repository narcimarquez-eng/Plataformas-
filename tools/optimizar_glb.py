"""Optimiza modelos .glb del juego con Blender (bpy).

Uso (Blender en modo consola):
  blender -b -P tools/optimizar_glb.py -- <archivo.glb|carpeta> <salida.glb|carpeta> [--ratio 0.5] [--umbral 400]

Uso (módulo bpy de pip):
  python tools/optimizar_glb.py -- <archivo.glb|carpeta> <salida.glb|carpeta>

Qué hace con cada modelo:
- Decima a la mitad las mallas con más triángulos que --umbral (Decimate, colapso),
  salvo los nodos con nombre: Blender desplaza su origen al decimar y el pivote de
  la animación cambiaría (p. ej. el aleteo de wingL/wingR).
- Exporta GLB sin modificar la jerarquía ni las transformaciones de los nodos.
- Restaura los nombres de los nodos: el juego anima partes por nombre
  (head, wingL, legFL...) y Blender pone nombres automáticos (Mesh_1...)
  a los nodos que no tenían nombre. Los nodos sin nombre quedan sin nombre.

Después, para comprimir la geometría (meshopt, decodificado por three.js):
  npx @gltf-transform/cli meshopt <salida.glb> <salida_final.glb>
"""
import argparse
import json
import os
import re
import struct
import sys

import bpy


def leer_argumentos():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(description="Optimiza .glb con Blender")
    p.add_argument("entrada")
    p.add_argument("salida")
    p.add_argument("--ratio", type=float, default=0.5, help="proporción de triángulos a conservar")
    p.add_argument("--umbral", type=int, default=400, help="decimar solo mallas con más triángulos que esto")
    return p.parse_args(argv)


def leer_glb(ruta):
    with open(ruta, "rb") as f:
        datos = f.read()
    clen, ctype = struct.unpack_from("<I4s", datos, 12)
    assert ctype == b"JSON", ruta
    js = json.loads(datos[20:20 + clen])
    resto = datos[20 + clen:]
    return js, resto


def escribir_glb(ruta, js, resto):
    jb = json.dumps(js, separators=(",", ":")).encode("utf-8")
    jb += b" " * ((4 - len(jb) % 4) % 4)
    total = 12 + 8 + len(jb) + len(resto)
    with open(ruta, "wb") as f:
        f.write(struct.pack("<4sII", b"glTF", 2, total))
        f.write(struct.pack("<I4s", len(jb), b"JSON"))
        f.write(jb)
        f.write(resto)


def restaurar_nombres(js_salida, js_orig):
    # Nodos: solo se conservan los nombres que tenían en el original
    originales = {n.get("name", "") for n in js_orig.get("nodes", []) if n.get("name")}
    for nodo in js_salida.get("nodes", []):
        nombre = nodo.get("name", "")
        if nombre in originales:
            continue
        # Blender añade ".001" a los nombres repetidos: devolvemos el original
        m = re.match(r"^(.+)\.\d{3}$", nombre)
        if m and m.group(1) in originales:
            nodo["name"] = m.group(1)
        else:
            nodo.pop("name", None)
    # Mallas y escenas: three.js usa el nombre de la malla si el nodo no tiene nombre
    mallas_orig = {m.get("name", "") for m in js_orig.get("meshes", []) if m.get("name")}
    for malla in js_salida.get("meshes", []):
        if malla.get("name", "") not in mallas_orig:
            malla.pop("name", None)
    for esc_sal, esc_orig in zip(js_salida.get("scenes", []), js_orig.get("scenes", [])):
        if esc_orig.get("name"):
            esc_sal["name"] = esc_orig["name"]
        else:
            esc_sal.pop("name", None)


def optimizar(entrada, salida, ratio, umbral):
    js_orig, _ = leer_glb(entrada)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=entrada)

    nombres_nodos = {n.get("name", "") for n in js_orig.get("nodes", []) if n.get("name")}
    decimadas = 0
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        base = re.sub(r"\.\d{3}$", "", obj.name)
        if obj.name in nombres_nodos or base in nombres_nodos:
            continue
        obj.data.calc_loop_triangles()
        if len(obj.data.loop_triangles) > umbral:
            mod = obj.modifiers.new(name="Decimate", type="DECIMATE")
            mod.ratio = ratio
            mod.use_collapse_triangulate = True
            decimadas += 1

    tmp = salida + ".tmp.glb"
    bpy.ops.export_scene.gltf(
        filepath=tmp,
        export_format="GLB",
        export_apply=True,
        export_cameras=False,
        export_lights=False,
    )

    js_sal, resto = leer_glb(tmp)
    restaurar_nombres(js_sal, js_orig)
    escribir_glb(salida, js_sal, resto)
    os.remove(tmp)
    print(f"[optimizar_glb] {os.path.basename(entrada)}: {decimadas} mallas decimadas -> {salida}")


def main():
    args = leer_argumentos()
    if os.path.isdir(args.entrada):
        os.makedirs(args.salida, exist_ok=True)
        archivos = sorted(f for f in os.listdir(args.entrada) if f.lower().endswith(".glb"))
        for nombre in archivos:
            optimizar(os.path.join(args.entrada, nombre),
                      os.path.join(args.salida, nombre), args.ratio, args.umbral)
    else:
        destino_dir = os.path.dirname(args.salida)
        if destino_dir:
            os.makedirs(destino_dir, exist_ok=True)
        optimizar(args.entrada, args.salida, args.ratio, args.umbral)


if __name__ == "__main__":
    main()
