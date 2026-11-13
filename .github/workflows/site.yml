name: Chiffres du clan et publication du site

on:
  push:
    branches: [main]        # à chaque modification du site
  schedule:
    - cron: "*/15 * * * *"  # toutes les 15 minutes (GitHub peut décaler un passage de quelques minutes)
  workflow_dispatch:        # bouton « Run workflow » dans l'onglet Actions

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Installer les outils d'image
        continue-on-error: true   # sans eux, les chiffres se mettent quand même à jour (seules les icônes restent celles de la page)
        run: pip install --quiet pillow numpy scipy

      - name: Récupérer les chiffres du clan
        continue-on-error: true   # si l'API ne répond pas, le site est publié quand même avec les chiffres écrits dans la page
        env:
          COC_TOKEN: ${{ secrets.COC_TOKEN }}
        run: python3 .github/workflows/scripts/clan.py

      - uses: actions/configure-pages@v5

      - uses: actions/upload-pages-artifact@v3
        with:
          path: .

      - id: deployment
        uses: actions/deploy-pages@v4
