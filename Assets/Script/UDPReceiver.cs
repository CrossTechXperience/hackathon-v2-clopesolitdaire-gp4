using UnityEngine;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;

public class UDPReceiver : MonoBehaviour
{
    [Header("Configuration")]
    public int port = 5005; // Doit correspondre à ton script Python

    [Header("Data (Read Only)")]
    public string lastReceivedPacket = ""; // Tu verras la valeur changer ici
    public float currentStressScore = 0f;  // La valeur convertie en nombre

    private Thread receiveThread;
    private UdpClient client;
    private bool isRunning = true;

    void Start()
    {
        receiveThread = new Thread(new ThreadStart(ReceiveData));
        receiveThread.IsBackground = true;
        receiveThread.Start();
        Debug.Log($"UDP Receiver démarré sur le port {port}...");
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

                    // Conversion des bytes en texte
                    string text = Encoding.UTF8.GetString(data);

                    // On stocke la donnée pour l'Update()
                    lastReceivedPacket = text;

                    // On essaie de convertir en nombre (float)
                    // "CultureInfo.InvariantCulture" est vital pour gérer le point "." vs virgule ","
                    if (float.TryParse(text, System.Globalization.NumberStyles.Any, System.Globalization.CultureInfo.InvariantCulture, out float result))
                    {
                        currentStressScore = result;
                    }
                }
                catch (System.Exception err)
                {
                    // On ignore les erreurs mineures de timeout
                    // Debug.Log(err.ToString());
                }
            }
        }
        catch (System.Exception e)
        {
            Debug.LogError("Erreur UDP: " + e.Message);
        }
    }

    // Le Thread Unity principal lit les valeurs reçues par le Thread UDP
    void Update()
    {
        // Simple test visuel : Si on reçoit des données, on l'affiche
        // Tu peux désactiver ce log si ça spamme trop
        // Debug.Log($"Reçu: {lastReceivedPacket} | Stress: {currentStressScore}");
    }

    void OnApplicationQuit()
    {
        // Nettoyage très important pour ne pas bloquer le port
        isRunning = false;
        if (client != null) client.Close();
        if (receiveThread != null) receiveThread.Abort();
        Debug.Log("UDP Receiver arrêté.");
    }
}
