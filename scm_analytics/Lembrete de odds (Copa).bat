@echo off
REM ============================================================================
REM  Lembrete de captura da LINHA DE FECHAMENTO (CLV real) — Copa 2026
REM  Roda o "watcher": avisa (console + pop-up) ~5 min antes de cada jogo que
REM  ainda nao tem odds 'close' gravadas. Voce ve o aviso, pega a odd de onde ja
REM  olha, e cola:  python -m scm.odds_close set "Casa" "Fora" CASA EMPATE FORA
REM  Deixe esta janela ABERTA no dia do jogo. Ctrl+C encerra.
REM  Dica: preencha o horario em dados/fixtures.json (campo "kickoff" ISO) p/
REM  o aviso no T-5min; sem horario, ele avisa no dia do jogo.
REM ============================================================================
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m scm.odds_close watch --lead 5 --poll 5
) else (
  python -m scm.odds_close watch --lead 5 --poll 5
)
echo.
pause
