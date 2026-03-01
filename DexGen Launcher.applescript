on run
	set appBundlePath to POSIX path of (path to me)
	set projectDir to do shell script "dirname " & quoted form of appBundlePath
	set launcherScript to projectDir & "/Launch DexGen.command"
	
	if (do shell script "test -f " & quoted form of launcherScript & " && echo yes || echo no") is "no" then
		display dialog "Launch script not found:\n" & launcherScript buttons {"OK"} default button "OK" with icon stop
		return
	end if
	
	do shell script "chmod +x " & quoted form of launcherScript
	do shell script "nohup " & quoted form of launcherScript & " >/tmp/dexgen-launcher.log 2>&1 &"
end run
