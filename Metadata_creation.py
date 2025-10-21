import argparse
import csv
import os
import re
import sys
from pathlib import Path
import wave

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour générer un CSV de metadata à partir d'un dossier d'audio.
Placez ce fichier dans /C:/Users/augus/OneDrive/Documents/Cours/ACO/M2/Machine Learning/Projet chat/Script base.py
Usage (exemples):
    python "Script base.py" /chemin/vers/dossier_audio
    python "Script base.py" /chemin/vers/dossier_audio --output meta.csv --regex "(?P<sujet>[^_]+)_(?P<age>\d+)_(?P<gender>[MF])_.*"
    python "Script base.py" /chemin/vers/dossier_audio --delimiter "_"   # créera token_1, token_2, ...
Le script écrit un CSV contenant: filepath, filename, ext, size_bytes, duration_seconds (si déterminable) + colonnes extraites.
"""


# optional audio duration support
def get_duration_seconds(path: Path):
        """Try to return duration in seconds. Uses mutagen if available, else wave for WAV files."""
        try:
                audio = MutagenFile(str(path))
                if audio and hasattr(audio.info, "length"):
                        return float(audio.info.length)
        except Exception:
                pass

        # fallback for wav files
        if path.suffix.lower() in (".wav",):
                try:
                        with wave.open(str(path), "rb") as wf:
                                frames = wf.getnframes()
                                framerate = wf.getframerate()
                                if framerate > 0:
                                        return frames / float(framerate)
                except Exception:
                        pass

        return None


def scan_directory(base: Path, exts=None, recursive=True):
        if exts:
                exts = {e.lower() if e.startswith('.') else f".{e.lower()}" for e in exts}
        files = []
        if recursive:
                it = base.rglob("*")
        else:
                it = base.iterdir()
        for p in it:
                if p.is_file():
                        if exts:
                                if p.suffix.lower() in exts:
                                        files.append(p)
                        else:
                                files.append(p)
        return sorted(files)


def main():
        ap = argparse.ArgumentParser(description="Créer un CSV de metadata depuis des fichiers audio (parsing depuis le nom).")
        ap.add_argument("C:/Users/augus/OneDrive/Documents/Cours/ACO/M2/Machine Learning\Projet chat\DeepMeows\dataset"", help="Dossier contenant les fichiers audio")
        ap.add_argument("--output", "-o", default="metadata.csv", help="Fichier CSV de sortie")
        ap.add_argument("--regex", "-r", help="Regex (avec groupes nommés) pour extraire metadata depuis le nom de fichier (sans extension). Exemple: '(?P<sujet>[^_]+)_(?P<age>\\d+)'")
        ap.add_argument("--delimiter", "-d", default=None, help="Si pas de regex, on splitte le nom par ce délimiteur. Ex: '_'")
        ap.add_argument("--exts", "-e", nargs="*", default=None, help="Extensions à inclure (ex: wav mp3). Par défaut toutes.")
        ap.add_argument("--no-recursive", action="store_true", help="Ne pas scanner récursivement")
        ap.add_argument("--skip-duration", action="store_true", help="Ne pas tenter de calculer la durée (gain de temps)")
        args = ap.parse_args()

        base = Path(args.input_dir)
        if not base.exists() or not base.is_dir():
                print("Le dossier d'entrée n'existe pas ou n'est pas un dossier.", file=sys.stderr)
                sys.exit(1)

        files = scan_directory(base, exts=args.exts, recursive=not args.no_recursive)
        if not files:
                print("Aucun fichier trouvé.", file=sys.stderr)
                sys.exit(1)

        use_regex = bool(args.regex)
        regex = re.compile(args.regex) if args.regex else None
        use_split = (args.delimiter is not None) and not use_regex

        rows = []
        max_tokens = 0

        for p in files:
                filename = p.name
                name_wo_ext = p.stem
                ext = p.suffix.lower()
                size = None
                try:
                        size = p.stat().st_size
                except Exception:
                        size = None

                duration = None
                if not args.skip_duration:
                        duration = get_duration_seconds(p)

                row = {
                        "filepath": str(p.resolve()),
                        "filename": filename,
                        "name": name_wo_ext,
                        "ext": ext,
                        "size_bytes": size,
                        "duration_seconds": duration,
                }

                if use_regex:
                        m = regex.match(name_wo_ext)
                        if m:
                                for k, v in m.groupdict().items():
                                        row[k] = v
                        else:
                                # keep empty for those groups if no match
                                for g in regex.groupindex.keys():
                                        row.setdefault(g, None)
                elif use_split:
                        tokens = name_wo_ext.split(args.delimiter)
                        max_tokens = max(max_tokens, len(tokens))
                        for i, t in enumerate(tokens, start=1):
                                row[f"token_{i}"] = t
                # else: no parsing

                rows.append(row)

        # if split used, ensure consistent columns token_1..token_max
        token_cols = [f"token_{i}" for i in range(1, max_tokens + 1)] if use_split else []

        # determine extra columns from regex group names if used
        extra_cols = []
        if use_regex and regex:
                # groupindex is a dict name->index
                extra_cols = list(regex.groupindex.keys())

        # build fieldnames in stable order
        base_cols = ["filepath", "filename", "name", "ext", "size_bytes", "duration_seconds"]
        fieldnames = base_cols + extra_cols + token_cols

        # ensure all rows have keys
        for r in rows:
                for c in fieldnames:
                        if c not in r:
                                r[c] = None

        # write CSV
        out_path = Path(args.output)
        try:
                with out_path.open("w", newline="", encoding="utf-8") as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        for r in rows:
                                writer.writerow(r)
                print(f"CSV écrit: {out_path.resolve()}")
        except Exception as exc:
                print("Erreur à l'écriture du CSV:", exc, file=sys.stderr)
                sys.exit(1)


if __name__ == "__main__":
        main()