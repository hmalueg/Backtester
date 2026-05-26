var program = new Program();
program.Run();

public partial class Program
{
    private Backtester.Loader _loader;

    public Program()
    {
        _loader = new Backtester.Loader();
    }

    public void Run()
    {
        Console.WriteLine("Application started. Press Ctrl+C to exit.");
        _loader.Start();

        // Keep the program running until user stops it
        while (true)
        {
            System.Threading.Thread.Sleep(100);
        }
    }
}
