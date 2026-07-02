@echo off
REM ============================================================================
REM TESTE COMPLETO: Sistema de Blocos Líquidos
REM ============================================================================
echo.
echo ================================================================
echo TESTE: CSS Design System Tokens
echo ================================================================
python tests\test_css_design_tokens.py

echo.
echo ================================================================
echo TESTE: Python Unit Tests (pytest)
echo ================================================================
python -m pytest tests\test_liquid_blocks.py -v --tb=short 2>&1 | head -80

echo.
echo ================================================================
echo FIM DOS TESTES
echo ================================================================
pause
