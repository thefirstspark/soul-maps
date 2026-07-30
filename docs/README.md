# Soul Maps — docs

## Algorithm specification (filing copy)

| File | Purpose |
|------|---------|
| `Soul_Map_Generator_Algorithm_Spec.pdf` | Full algorithm + audit record for IP / engineering filing |
| `build_algorithm_pdf.py` | Rebuild the PDF from source |

```bash
cd soul-maps
python docs/build_algorithm_pdf.py
```

Also writes a Desktop copy: `~/Desktop/Soul_Map_Generator_Algorithm_Spec.pdf`.

## Related source

- Generator: `../soul_map_generator.py`
- Webhook: `../webhook_server.py`
- Setup: `../WEBHOOK_SETUP.md`
