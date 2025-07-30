@echo off
chcp 65001 >nul

echo ========================================
echo [INFO] Running update script at %date% %time%
echo ========================================

:: 激活虚拟环境（前提是你使用了 .venv）
call .venv\Scripts\activate

echo [STEP 1] Running sentiment_calculator.py...
python sentiment_calculator.py
if errorlevel 1 (
    echo [ERROR] Python failed. Exiting.
    pause
    exit /b
)

echo [STEP 2] Git commit and push...
git add cyb_sentiment.csv
git commit -m "📈 Update sentiment data %date% %time%"
git push

echo [DONE] Successfully pushed to GitHub!
pause
