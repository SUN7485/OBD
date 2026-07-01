$currentPath = [System.Environment]::GetEnvironmentVariable('PATH', 'User')
if ($currentPath -notlike '*Android\Sdk*') {
    [System.Environment]::SetEnvironmentVariable('PATH', $currentPath + ';C:\Users\mosun\AppData\Local\Android\Sdk\platform-tools', 'User')
    [System.Environment]::SetEnvironmentVariable('ANDROID_HOME', 'C:\Users\mosun\AppData\Local\Android\Sdk', 'User')
}