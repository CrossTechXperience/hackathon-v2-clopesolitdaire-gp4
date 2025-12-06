using UnityEngine;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;

public class UDPReceiver : MonoBehaviour
{
    [Header("Configuration")]
    public int port = 5005; // Same number as the sender

    [Header("Data (Read Only)")]
    public string lastReceivedPacket = ""; 
    public float currentStressScore = 0f;  
    private Thread receiveThread;
    private UdpClient client;
    private bool isRunning = true;

    void Start()
    {
        receiveThread = new Thread(new ThreadStart(ReceiveData));
        receiveThread.IsBackground = true;
        receiveThread.Start();
        Debug.Log($"UDP Receiver started on port {port}...");
    }

    private void ReceiveData()
    {
        try
        {
            client = new UdpClient(port);
            while (isRunning)
            {
                try
                {
                    IPEndPoint anyIP = new IPEndPoint(IPAddress.Any, 0);
                    byte[] data = client.Receive(ref anyIP);

                    
                    string text = Encoding.UTF8.GetString(data);

                    lastReceivedPacket = text;

                   
                    if (float.TryParse(text, System.Globalization.NumberStyles.Any, System.Globalization.CultureInfo.InvariantCulture, out float result))
                    {
                        currentStressScore = result;
                    }
                }
                catch (System.Exception err)
                {
                    // We ignore minor timeout errors
                    // Debug.Log(err.ToString());
                }
            }
        }
        catch (System.Exception e)
        {
            Debug.LogError("UDP error: " + e.Message);
        }
    }


    // The main Unity thread reads the values received by the UDP thread
    void Update()
    {
        // Debug.Log($"Received: {lastReceivedPacket} | Stress: {currentStressScore}");
    }

    void OnApplicationQuit()
    {
        // cleanup to avoid blocking the port
        isRunning = false;
        if (client != null) client.Close();
        if (receiveThread != null) receiveThread.Abort();
        Debug.Log("UDP Receiver stopped.");
    }
}
