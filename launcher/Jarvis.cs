using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

internal static class Jarvis
{
    private static readonly string Project = AppDomain.CurrentDomain.BaseDirectory;

    // Explorer can have a different PATH from an activated developer shell.
    private static IEnumerable<string> PythonDirectories()
    {
        yield return Path.Combine(Project, ".venv", "Scripts");
        yield return Path.Combine(Project, "venv", "Scripts");
        yield return Environment.GetEnvironmentVariable("CONDA_PREFIX");
        foreach (string dir in (Environment.GetEnvironmentVariable("PATH") ?? "").Split(';'))
            yield return dir.Trim().Trim('"');

        string profile = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
        string environments = Path.Combine(profile, ".conda", "environments.txt");
        if (File.Exists(environments))
            foreach (string dir in File.ReadAllLines(environments))
                yield return dir.Trim();
    }

    private static ProcessStartInfo StartInfo(string python, string arguments)
    {
        string dir = Path.GetDirectoryName(python);
        var info = new ProcessStartInfo(python, arguments) {
            WorkingDirectory = Project,
            UseShellExecute = false,
            CreateNoWindow = true
        };
        // Conda ships Qt, audio DLLs and Piper in these directories.
        info.EnvironmentVariables["PATH"] = String.Join(";", new[] {
            dir, Path.Combine(dir, "Library", "bin"), Path.Combine(dir, "Scripts"),
            info.EnvironmentVariables["PATH"]
        });
        return info;
    }

    private static string FindPython()
    {
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (string dir in PythonDirectories())
        {
            if (String.IsNullOrWhiteSpace(dir) || !Path.IsPathRooted(dir) || !seen.Add(dir))
                continue;
            string python = Path.Combine(dir, "pythonw.exe");
            // Microsoft Store execution aliases can open the Store during discovery.
            if (!File.Exists(python) || dir.EndsWith(@"\Microsoft\WindowsApps", StringComparison.OrdinalIgnoreCase))
                continue;
            const string probe = "-c \"from PySide6.QtWebEngineWidgets import QWebEngineView; import qasync; "
                + "import importlib.util as u, sys; sys.exit(not all(u.find_spec(m) for m in "
                + "('sounddevice','torch','faster_whisper','semantic_router')))\"";
            using (Process check = Process.Start(StartInfo(python, probe)))
            {
                if (!check.WaitForExit(15000)) {
                    check.Kill();
                    continue;
                }
                if (check.ExitCode == 0)
                    return python;
            }
        }
        throw new InvalidOperationException("Install requirements.txt in a project .venv, a Python environment on PATH, or a registered Conda environment.");
    }

    [STAThread]
    private static int Main()
    {
        try
        {
            if (!File.Exists(Path.Combine(Project, "jarvis_ui.py")))
                throw new FileNotFoundException("Place Jarvis.exe next to jarvis_ui.py in the Jarvis project folder.");
            using (Process app = Process.Start(StartInfo(FindPython(), "-u jarvis_ui.py")))
            {
                app.WaitForExit();
                if (app.ExitCode != 0)
                    throw new InvalidOperationException("The UI exited unexpectedly. Open the startup log at " + Path.Combine(Project, "jarvis.log"));
            }
            return 0;
        }
        catch (Exception error)
        {
            MessageBox.Show(error.Message, "Jarvis", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }
}
