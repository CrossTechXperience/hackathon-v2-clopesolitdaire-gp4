using System;
using UnityEngine;

public class EyesTrackingSimulation : MonoBehaviour
{
    [SerializeField] Camera mainCamera;
    
    [Header("Raycast")]
    [SerializeField] float rayDistance = 50f;
    [SerializeField] GameObject prefabObject;

    [Header("Trigger")] 
    [SerializeField] private float timeToTrigger = 1f; // pas utilisé ici pour couleur random
    [SerializeField] private float spawnDistance = 2f;

    private GameObject currentLookObject;
    private float lookTimer = 0f;
    private float colorChangeTimer = 0f;
    private float colorChangeInterval = 2f;

    private void Update()
    {
        if (mainCamera == null) return;

        Ray ray = new Ray(mainCamera.transform.position, mainCamera.transform.forward);
        RaycastHit hit;
        Debug.DrawRay(mainCamera.transform.position, mainCamera.transform.forward * rayDistance, Color.green, 0f);

        if (Physics.Raycast(ray, out hit, rayDistance))
        {
            GameObject go = hit.collider.gameObject;

            if (go != currentLookObject)
            {
                ResetPreviousObject();
                currentLookObject = go;
                lookTimer = 0f;
                colorChangeTimer = 0f;
            }
            if (go.GetComponent<EyesTrigger>() != null)
            {
                colorChangeTimer += Time.deltaTime;
                if (colorChangeTimer >= colorChangeInterval)
                {
                    Renderer rend = go.GetComponent<Renderer>();
                    if (rend != null)
                    {
                        rend.material.color = new Color(
                            UnityEngine.Random.value,
                            UnityEngine.Random.value,
                            UnityEngine.Random.value
                        );
                    }
                    colorChangeTimer = 0f;
                }
            }
            if (go.GetComponent<ObjectToSpawn>() != null)
            {
                Vector3 leftSpawn = go.transform.position - go.transform.right * spawnDistance;
                Instantiate(prefabObject, leftSpawn, Quaternion.identity);
            }
        }
        else
        {
            ResetPreviousObject();
        }
    }

    private void ResetPreviousObject()
    {
        if (currentLookObject != null)
        {
            Renderer rend = currentLookObject.GetComponent<Renderer>();
            if (rend != null && currentLookObject.GetComponent<EyesTrigger>() != null)
                rend.material.color = Color.white;
        }

        currentLookObject = null;
        lookTimer = 0f;
        colorChangeTimer = 0f;
    }
}
