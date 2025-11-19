@echo off
REM ------------------------------------------------
REM CANoe 19 Remote Automation
REM ------------------------------------------------

REM Path to CANoe configuration file
SET CANOE_CFG="C:\Users\Public\Documents\Vector\CANoe\Projects\CAN_500kBaud_2ch\CAN_500kBaud_2ch.cfg"

REM Path to CANoe executable
SET CANOE_EXE="C:\Program Files\Vector CANoe 19\Exec64\CANoe64.exe"

REM Start CANoe visibly (no /MIN)
START "" %CANOE_EXE% %CANOE_CFG% /AutoMeasure

REM Wait until CANoe exits
:waitLoop
timeout /t 5 /nobreak >nul
tasklist /fi "imagename eq CANoe64.exe" | find /i "CANoe64.exe" >nul
IF NOT ERRORLEVEL 1 (
    REM Still running, wait 5 seconds
    GOTO waitLoop
)

ECHO CANoe measurement finished. BLF should be in the project Logs folder.
