using UnityEngine;
using UnityEngine.UI;

public class StressScore : MonoBehaviour
{
    [Header("Sources")]
    public UDPReceiver receiver;   // référence à ton UDPReceiver (instance dans la scène)
    public Image progressBar;      // Image (type = Filled)

    [Header("Mapping")]
    public float minValue = 0f;
    public float maxValue = 1000f; // clamp max
    public bool invert = false;    // si true => 1000 = empty, 0 = full

    [Header("Smoothing")]
    [Tooltip("Vitesse à laquelle la barre atteint la nouvelle valeur (units/sec). Plus grand = plus rapide.")]
    public float smoothSpeed = 2f;

    [Header("Color thresholds")]
    public float stressThreshold = 40f;   
    public float goodThreshold = 800f;    

    // internal
    private float displayedNormalized = 0f; 
    private Color targetColor = Color.white;

    void Start()
    {
        if (progressBar == null)
            Debug.LogWarning("ProgressBar not set on StressScore.");
        // init displayed value to current receiver value if available
        if (receiver != null)
        {
            float val = Mathf.Clamp(receiver.currentStressScore, minValue, maxValue);
            displayedNormalized = Normalize(val);
            UpdateBarImmediate(displayedNormalized);
        }
    }

    void Update()
    {
        if (receiver == null || progressBar == null) return;

        float raw = Mathf.Clamp(receiver.currentStressScore, minValue, maxValue);


        float normalized = Normalize(raw);

        if (invert) normalized = 1f - normalized;

        displayedNormalized = Mathf.MoveTowards(displayedNormalized, normalized, smoothSpeed * Time.deltaTime);

        progressBar.fillAmount = displayedNormalized;

        if (raw <= stressThreshold)
            targetColor = Color.red;
        else if (raw >= goodThreshold)
            targetColor = Color.green;
        else
            targetColor = Color.yellow;

        // lissage couleur
        progressBar.color = Color.Lerp(progressBar.color, targetColor, 6f * Time.deltaTime);
    }

    private float Normalize(float raw)
    {
        if (Mathf.Approximately(maxValue, minValue)) return 0f;
        return Mathf.Clamp01((raw - minValue) / (maxValue - minValue));
    }

    private void UpdateBarImmediate(float normalized)
    {
        progressBar.fillAmount = normalized;
        // set color immediately
        if (normalized <= (stressThreshold - minValue) / Mathf.Max(1e-6f, maxValue - minValue))
            progressBar.color = Color.red;
        else if (normalized >= (goodThreshold - minValue) / Mathf.Max(1e-6f, maxValue - minValue))
            progressBar.color = Color.green;
        else
            progressBar.color = Color.yellow;
    }
}
