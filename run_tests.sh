#!/bin/bash

##
# Script pour exécuter les tests du backend
#
# Usage:
#   ./run_tests.sh                  # Tous les tests
#   ./run_tests.sh integration      # Tests d'intégration uniquement
#   ./run_tests.sh coverage         # Tests avec rapport de coverage
#   ./run_tests.sh unit             # Tests unitaires uniquement
##

set -e

# Couleurs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Banner
echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Tests - Orchestrateur IA Backend    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# Vérifier que Docker tourne
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker n'est pas démarré${NC}"
    exit 1
fi

# Vérifier que le container backend existe
if ! docker ps -a --format '{{.Names}}' | grep -q "orchestrator-backend"; then
    echo -e "${RED}❌ Container orchestrator-backend introuvable${NC}"
    echo -e "${YELLOW}💡 Lancer d'abord: ./start.sh${NC}"
    exit 1
fi

# Fonction pour exécuter les tests
run_tests() {
    local cmd=$1
    local description=$2

    echo -e "${BLUE}🧪 $description${NC}"
    echo ""

    if docker exec orchestrator-backend python -m $cmd; then
        echo ""
        echo -e "${GREEN}✅ Tests réussis!${NC}"
        return 0
    else
        echo ""
        echo -e "${RED}❌ Tests échoués${NC}"
        return 1
    fi
}

# Parser les arguments
case "${1:-all}" in
    "integration")
        echo -e "${YELLOW}Mode: Tests d'intégration uniquement${NC}"
        echo ""
        run_tests "pytest tests/integration/ -v" "Tests d'intégration"
        ;;

    "unit")
        echo -e "${YELLOW}Mode: Tests unitaires uniquement${NC}"
        echo ""
        run_tests "pytest tests/unit/ -v" "Tests unitaires"
        ;;

    "coverage")
        echo -e "${YELLOW}Mode: Tests avec coverage${NC}"
        echo ""
        run_tests "pytest --cov=app --cov-report=term-missing --cov-report=html" "Tests avec coverage"
        echo ""
        echo -e "${GREEN}📊 Rapport HTML généré: backend/htmlcov/index.html${NC}"
        echo -e "${BLUE}💡 Ouvrir avec: open backend/htmlcov/index.html${NC}"
        ;;

    "workflow")
        echo -e "${YELLOW}Mode: Test workflow complet${NC}"
        echo ""
        run_tests "pytest tests/integration/test_full_workflow.py -v" "Test workflow complet"
        ;;

    "orchestrator")
        echo -e "${YELLOW}Mode: Tests orchestrateur${NC}"
        echo ""
        run_tests "pytest tests/integration/test_orchestrator.py -v" "Tests orchestrateur"
        ;;

    "quick")
        echo -e "${YELLOW}Mode: Tests rapides (sans verbose)${NC}"
        echo ""
        run_tests "pytest -q" "Tests rapides"
        ;;

    "debug")
        echo -e "${YELLOW}Mode: Debug (avec prints et traceback complet)${NC}"
        echo ""
        run_tests "pytest -vv --tb=long -s" "Tests en mode debug"
        ;;

    "watch")
        echo -e "${YELLOW}Mode: Watch (re-run automatique)${NC}"
        echo ""
        echo -e "${BLUE}💡 Installez pytest-watch: pip install pytest-watch${NC}"
        run_tests "ptw tests/" "Watch mode"
        ;;

    "all"|*)
        echo -e "${YELLOW}Mode: Tous les tests${NC}"
        echo ""
        run_tests "pytest -v" "Tous les tests"
        ;;
esac

exit_code=$?

echo ""
echo -e "${BLUE}════════════════════════════════════════${NC}"

if [ $exit_code -eq 0 ]; then
    echo -e "${GREEN}✨ Succès!${NC}"
else
    echo -e "${RED}💥 Échec${NC}"
fi

echo -e "${BLUE}════════════════════════════════════════${NC}"

exit $exit_code
