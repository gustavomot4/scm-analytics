@echo off
cd /d "%~dp0"
title SCM - Previsao Copa 2026
echo ============================================
echo   SCM - Sistema de Previsao da Copa 2026
echo ============================================
echo.
REM Detecta o Python (py launcher ou python no PATH)
where py >nul 2>nul
if %errorlevel%==0 (set "PY=py") else (set "PY=python")

REM 1) Ambiente virtual (CONFIGURA na primeira vez: cria venv + instala dependencias)
if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Primeira vez: criando ambiente e instalando dependencias...
  %PY% -m venv .venv
  call ".venv\Scripts\activate.bat"
  python -m pip install --upgrade pip >nul
  pip install -r requirements.txt
  if errorlevel 1 ( echo. & echo [ERRO] Falha ao instalar dependencias ^(verifique a internet^). & pause & exit /b 1 )
) else (
  call ".venv\Scripts\activate.bat"
)

REM 2) Base de dados (CONSTROI na primeira vez: baixa dados + pipeline completo)
if not exist "dados\scm.sqlite" (
  echo [2/3] Construindo a base pela primeira vez ^(baixa dados, ~1-2 min^)...
  python -m scm.ingest --download && python -m scm.ingest && python -m scm.elo_engine && python -m scm.features_pit && python -m scm.predictor
  if errorlevel 1 ( echo. & echo [ERRO] Falha ao construir a base. & pause & exit /b 1 )
)

REM 3) Abre o sistema (servidor local + navegador). Dados frescos: botao "Atualizar tudo" na tela.
echo [3/3] Abrindo o sistema no navegador (http://127.0.0.1:5000)...
echo.
echo   ^>^> Esta janela = servidor rodando. Para SAIR: feche a janela (ou Ctrl+C).
echo.
python -m scm.web --open
pause
