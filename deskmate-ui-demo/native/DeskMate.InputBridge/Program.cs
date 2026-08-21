using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;
using System.Windows.Forms;

namespace DeskMate.InputBridge;

internal static class Program
{
    [STAThread]
    private static void Main(string[] args)
    {
        Console.OutputEncoding = new UTF8Encoding(false);
        if (args.Contains("--self-test", StringComparer.OrdinalIgnoreCase))
        {
            var writer = new EventWriter();
            writer.Input("easyinput-hid", "F22", "down");
            writer.Input("easyinput-hid", "F22", "up");
            writer.Status(false);
            return;
        }

        Application.SetHighDpiMode(HighDpiMode.PerMonitorV2);
        using var window = new RawInputWindow(new EventWriter());
        Application.Run();
    }
}

internal sealed class EventWriter
{
    private readonly object _sync = new();
    private long _sequence;

    public void Input(string source, string key, string action) => Write(new BridgeEvent(
        1, "input", source, key, action, DateTimeOffset.UtcNow, Interlocked.Increment(ref _sequence), null));

    public void Status(bool connected) => Write(new BridgeEvent(
        1, "status", "easyinput-hid", "Device", connected ? "connected" : "disconnected",
        DateTimeOffset.UtcNow, Interlocked.Increment(ref _sequence), connected));

    private void Write(BridgeEvent value)
    {
        lock (_sync)
        {
            Console.Out.WriteLine(JsonSerializer.Serialize(value, BridgeJsonContext.Default.BridgeEvent));
            Console.Out.Flush();
        }
    }
}

internal sealed record BridgeEvent(
    int version,
    string type,
    string source,
    string key,
    string action,
    DateTimeOffset time,
    long sequence,
    bool? boardConnected);

[System.Text.Json.Serialization.JsonSerializable(typeof(BridgeEvent))]
internal partial class BridgeJsonContext : System.Text.Json.Serialization.JsonSerializerContext;

internal sealed class RawInputWindow : NativeWindow, IDisposable
{
    private const int WmInput = 0x00FF;
    private const int WmInputDeviceChange = 0x00FE;
    private const uint RidInput = 0x10000003;
    private const uint RidiDeviceName = 0x20000007;
    private const uint RimTypeKeyboard = 1;
    private const ushort HidUsagePageGeneric = 0x01;
    private const ushort HidUsageGenericKeyboard = 0x06;
    private const uint RidevInputSink = 0x00000100;
    private const uint RidevDeviceNotify = 0x00002000;
    private const ushort RiKeyBreak = 0x0001;
    private const ushort RiKeyE0 = 0x0002;
    private const ushort VkMenu = 0x12;
    private const ushort VkEscape = 0x1B;
    private const ushort VkRMenu = 0xA5;
    private const ushort VkF22 = 0x85;
    private const string BoardVidPid = "VID_303A&PID_1006";

    private readonly EventWriter _writer;
    private bool _boardConnected;
    private bool _disposed;

    public RawInputWindow(EventWriter writer)
    {
        _writer = writer;
        CreateHandle(new CreateParams { Caption = "DeskMate Raw Input Bridge", Parent = new IntPtr(-3) });
        RegisterKeyboard();
        RefreshBoardStatus(force: true);
    }

    protected override void WndProc(ref Message m)
    {
        if (m.Msg == WmInput) ReadInput(m.LParam);
        else if (m.Msg == WmInputDeviceChange) RefreshBoardStatus(force: false);
        base.WndProc(ref m);
    }

    private void RegisterKeyboard()
    {
        var devices = new[]
        {
            new RawInputDevice
            {
                UsagePage = HidUsagePageGeneric,
                Usage = HidUsageGenericKeyboard,
                Flags = RidevInputSink | RidevDeviceNotify,
                Target = Handle,
            },
        };
        if (!RegisterRawInputDevices(devices, 1, (uint)Marshal.SizeOf<RawInputDevice>()))
            throw new InvalidOperationException($"Raw Input registration failed: {Marshal.GetLastWin32Error()}");
    }

    private void ReadInput(IntPtr inputHandle)
    {
        uint size = 0;
        var headerSize = (uint)Marshal.SizeOf<RawInputHeader>();
        if (GetRawInputData(inputHandle, RidInput, IntPtr.Zero, ref size, headerSize) != 0 || size < headerSize) return;
        var buffer = Marshal.AllocHGlobal((int)size);
        try
        {
            if (GetRawInputData(inputHandle, RidInput, buffer, ref size, headerSize) != size) return;
            var header = Marshal.PtrToStructure<RawInputHeader>(buffer);
            if (header.Type != RimTypeKeyboard) return;
            var keyboard = Marshal.PtrToStructure<RawKeyboard>(IntPtr.Add(buffer, (int)headerSize));
            var name = GetDeviceName(header.Device);
            var board = name.Contains(BoardVidPid, StringComparison.OrdinalIgnoreCase);
            var isUp = (keyboard.Flags & RiKeyBreak) != 0;
            var action = isUp ? "up" : "down";

            if (board && keyboard.VKey == VkF22)
                _writer.Input("easyinput-hid", "F22", action);
            else if (keyboard.VKey == VkRMenu || (keyboard.VKey == VkMenu && (keyboard.Flags & RiKeyE0) != 0))
                _writer.Input("keyboard", "RightAlt", action);
            else if (keyboard.VKey == VkEscape)
                _writer.Input("keyboard", "Escape", action);
        }
        finally
        {
            Marshal.FreeHGlobal(buffer);
        }
    }

    private void RefreshBoardStatus(bool force)
    {
        var connected = EnumerateDeviceNames().Any(name => name.Contains(BoardVidPid, StringComparison.OrdinalIgnoreCase));
        if (!force && connected == _boardConnected) return;
        _boardConnected = connected;
        _writer.Status(connected);
    }

    private static IEnumerable<string> EnumerateDeviceNames()
    {
        uint count = 0;
        var itemSize = (uint)Marshal.SizeOf<RawInputDeviceList>();
        if (GetRawInputDeviceList(IntPtr.Zero, ref count, itemSize) != 0 || count == 0) yield break;
        var buffer = Marshal.AllocHGlobal(checked((int)(count * itemSize)));
        try
        {
            if (GetRawInputDeviceList(buffer, ref count, itemSize) == uint.MaxValue) yield break;
            for (var index = 0; index < count; index++)
            {
                var item = Marshal.PtrToStructure<RawInputDeviceList>(IntPtr.Add(buffer, checked((int)(index * itemSize))));
                if (item.Type == RimTypeKeyboard) yield return GetDeviceName(item.Device);
            }
        }
        finally
        {
            Marshal.FreeHGlobal(buffer);
        }
    }

    private static string GetDeviceName(IntPtr device)
    {
        uint length = 0;
        GetRawInputDeviceInfo(device, RidiDeviceName, null, ref length);
        if (length == 0) return string.Empty;
        var builder = new StringBuilder((int)length + 1);
        return GetRawInputDeviceInfo(device, RidiDeviceName, builder, ref length) == uint.MaxValue ? string.Empty : builder.ToString();
    }

    public void Dispose()
    {
        if (_disposed) return;
        _disposed = true;
        DestroyHandle();
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct RawInputDevice { public ushort UsagePage; public ushort Usage; public uint Flags; public IntPtr Target; }

    [StructLayout(LayoutKind.Sequential)]
    private struct RawInputDeviceList { public IntPtr Device; public uint Type; }

    [StructLayout(LayoutKind.Sequential)]
    private struct RawInputHeader { public uint Type; public uint Size; public IntPtr Device; public IntPtr WParam; }

    [StructLayout(LayoutKind.Sequential)]
    private struct RawKeyboard
    {
        public ushort MakeCode;
        public ushort Flags;
        public ushort Reserved;
        public ushort VKey;
        public uint Message;
        public uint ExtraInformation;
    }

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool RegisterRawInputDevices([In] RawInputDevice[] devices, uint count, uint size);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern uint GetRawInputData(IntPtr input, uint command, IntPtr data, ref uint size, uint headerSize);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern uint GetRawInputDeviceList(IntPtr list, ref uint count, uint size);

    [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern uint GetRawInputDeviceInfo(IntPtr device, uint command, StringBuilder? data, ref uint size);
}
