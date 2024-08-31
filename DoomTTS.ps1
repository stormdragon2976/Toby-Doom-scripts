# Change the next line to $true to enable the script
$useTextToSpeech = $false
# Set this to $true to use SAPI, $false to use nvdaControllerClient or fall back to clipboard
$useSAPI = $true
# Set the speech rate. -10 to 10, default 0
$speechRate = 0

# Do not edit below this line.
######################################################################

# Exit if text-to-speech is disabled
if (-not $useTextToSpeech) {
    exit
}

# Define antigrep, and sed patterns
$antigrepPatterns = @(
    '^P_StartScript:',
    '^[Ff]luidsynth:',
    '^(Facing|INTRO|MAP[0-9]+|README)',
    '^ *TITLEMAP',
    'key card',
    '^\[Toby Accessibility Mod\] (INTRO|READMe)([0-9]+).*',
    "^(As |Computer Voice:|I |I've|Monorail|Ugh|What|Where)",
    [regex]::Escape('Ugh... Huh? What the hell was that?! Better go check it out...')
)

$sedPatterns = @(
    @("\[Toby Accessibility Mod\] M_", "[Toby Accessibility Mod] "),
    @("^\[Toby Accessibility Mod\] ", ""),
    @("^MessageBoxMenu$", "Confirmation menu: Press Y for yes or N for no"),
    @("^Mainmenu$", "Main menu"),
    @("^Playerclassmenu$", "Player class menu"),
    @("^Skillmenu$", "Difficulty menu"),
    @("^NGAME", "New game"),
    @("^LOADG$", "Load game"),
    @("^SAVEG$", "Save game"),
    @("^QUITG$", "Quit game"),
    @('"cl_run" = "true"', "Run"),
    @('"cl_run" = "false"', "Walk"),
    @('.*/:Game saved. \(', ""),
    @('^\*\*\*', ""),
    @('^\+', "")
)

# Check PowerShell version
$requiredPowershellVersion = [Version]"5.1"
$currentPowershellVersion = $PSVersionTable.PSVersion

$logFile = ".\DoomTTS.log"
Set-Content -Path $logFile -Value "Logging started $(Get-Date -Format 'dddd MMMM dd, yyyy') at $(Get-Date -Format 'hh:mmtt')"
Add-Content -Path $logFile -Value "Powershell $currentPowershellVersion"
if ($currentVersion -lt $requiredVersion) {
    Add-Content -Path $logFile -Value "PowerShell version $requiredPowershellVersion or later is required. Exiting."
    exit
}

# Function for logging
function Write-Log {
    param (
        [string]$Message,
        [string]$Type = "INFO"  # Can be INFO, ERROR, or SPEECH
    )

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "$Message [$Type] [$timestamp]"
    
    # Append the message to the log file
    Add-Content -Path $logFile -Value $logMessage

    # If it's an error, also write to the console
    if ($Type -eq "ERROR") {
        Write-Host $logMessage -ForegroundColor Red
    }
}

# Function to load NVDA DLL and check if NVDA is running
function Initialize-NVDA {
    try {
        # Declare the P/Invoke signatures
        $signature = @"
        [DllImport("kernel32.dll")]
        public static extern IntPtr LoadLibrary(string dllToLoad);

        [DllImport("kernel32.dll")]
        public static extern IntPtr GetProcAddress(IntPtr hModule, string procedureName);

        [DllImport("kernel32.dll")]
        public static extern bool FreeLibrary(IntPtr hModule);

        [UnmanagedFunctionPointer(CallingConvention.StdCall)]
        public delegate int NvdaTestIfRunning();

        [UnmanagedFunctionPointer(CallingConvention.StdCall)]
        public delegate void NvdaSpeakText([MarshalAs(UnmanagedType.LPWStr)] string text);

        [UnmanagedFunctionPointer(CallingConvention.StdCall)]
        public delegate void NvdaBrailleMessage([MarshalAs(UnmanagedType.LPWStr)] string message);

        [UnmanagedFunctionPointer(CallingConvention.StdCall)]
        public delegate void NvdaCancelSpeech();
"@

        Add-Type -MemberDefinition $signature -Name "NvdaFunctions" -Namespace "Win32Functions"

        # Load the NVDA client library
        $dllPath = ".\nvdaControllerClient.dll"
        $nvdaDll = [Win32Functions.NvdaFunctions]::LoadLibrary($dllPath)
        if ($nvdaDll -eq [IntPtr]::Zero) {
            throw "Failed to load nvdaControllerClient.dll"
        }

        # Define function pointers
        $nvdaTestIfRunning = [System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer(
            [Win32Functions.NvdaFunctions]::GetProcAddress($nvdaDll, "nvdaController_testIfRunning"),
            [Type][Win32Functions.NvdaFunctions+NvdaTestIfRunning]
        )

        $nvdaSpeakText = [System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer(
            [Win32Functions.NvdaFunctions]::GetProcAddress($nvdaDll, "nvdaController_speakText"),
            [Type][Win32Functions.NvdaFunctions+NvdaSpeakText]
        )

        $nvdaBrailleMessage = [System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer(
            [Win32Functions.NvdaFunctions]::GetProcAddress($nvdaDll, "nvdaController_brailleMessage"),
            [Type][Win32Functions.NvdaFunctions+NvdaBrailleMessage]
        )

        $nvdaCancelSpeech = [System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer(
            [Win32Functions.NvdaFunctions]::GetProcAddress($nvdaDll, "nvdaController_cancelSpeech"),
            [Type][Win32Functions.NvdaFunctions+NvdaCancelSpeech]
        )

        # Test if NVDA is running
        $res = $nvdaTestIfRunning.Invoke()
        if ($res -ne 0) {
            $errorMessage = [ComponentModel.Win32Exception]::new([System.Runtime.InteropServices.Marshal]::GetLastWin32Error()).Message
            throw "NVDA is not running or communication failed. Error: $errorMessage"
        }

        return @{
            SpeakText = $nvdaSpeakText
            BrailleMessage = $nvdaBrailleMessage
            CancelSpeech = $nvdaCancelSpeech
        }
    }
    catch {
        Write-Log -Message "Error initializing NVDA: $_" -Type "ERROR"
        return $null
    }
}

# Function to speak text using SAPI, NVDA, or copy to clipboard
function Speak-Text {
    param (
        [string]$text
    )
    
    Write-Log -Message "Speaking: $text" -Type "SPEECH"
    
    if ($useSAPI) {
        try {
            $tts = New-Object -ComObject SAPI.SPVoice
            $tts.Rate = $speechRate
            $tts.Speak($text)
        } catch {
            Write-Log -Message "Error using SAPI: $_" -Type "ERROR"
        }
    } else {
        $nvdaFunctions = Initialize-NVDA
        if ($nvdaFunctions) {
            try {
                $nvdaFunctions.SpeakText.Invoke($text)
            } catch {
                Write-Log -Message "Error using nvdaControllerClient.dll: $_" -Type "ERROR"
                Set-Clipboard -Value $text
            }
        } else {
            Set-Clipboard -Value $text
            Write-Log -Message "Failed to initialize NVDA, text copied to clipboard" -Type "INFO"
        }
    }
}

# Process the output with grep, antigrep, and sed-like functionality
function Process-Output {
    param (
        [string]$line,
        [string[]]$antigrepPatterns,
        [array]$sedPatterns
    )

    # Apply antigrep (exclude lines)
    foreach ($pattern in $antigrepPatterns) {
        if ($line -match $pattern) {
            return  # Skip this line
        }
    }

    # Apply sed (modify lines)
    foreach ($pattern in $sedPatterns) {
        $line = $line -replace $pattern[0], $pattern[1]
    }

    return $line
}


# Start reading the piped output
$stream = [System.IO.StreamReader]::new([Console]::OpenStandardInput(), [System.Text.Encoding]::UTF8)
# Use the 40 - line to let us know when to start speaking.
$startProcessing = $false
                                                                                                                                                                          
while ($null -ne ($line = $stream.ReadLine())) {
    Write-Log -Message "Raw input: $line" -Type "INFO"
                                                                                                                                                                          
    # Check for the separator
    if ($line -match '^-{5,}$') {
        $startProcessing = $true
        continue  # Skip the separator
    }
                                                                                                                                                                          
    # Only process lines after we've seen the separator
    if ($startProcessing) {
        $processedLine = Process-Output -line $line -antigrepPatterns $antigrepPatterns -sedPatterns $sedPatterns
        if ($processedLine) {
            Write-Log -Message "Processed line: $processedLine" -Type "INFO"
            Speak-Text -text $processedLine
        }
    }
}
