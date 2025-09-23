# ComfyUI Encrypted Docker - Troubleshooting Guide

## 🚨 Common Pod Failures

### **1. ComfyUI Server Failed to Start**

**Error Message:**
```
RuntimeError: ComfyUI server failed to start
ERROR: Application startup failed. Exiting.
```

**Common Causes & Solutions:**

#### **A. GPU Detection Issues**
**Symptoms:**
```
WARNING: The NVIDIA Driver was not detected. GPU functionality will not be available.
```

**Solution:**
```bash
# Force CPU mode in Pod environment variables
FORCE_CPU=1
DEVICE_MODE=cpu
```

#### **B. Startup Timeout**
**Symptoms:**
- Pod takes longer than 5 minutes to start
- ComfyUI initialization hangs

**Solution:**
```bash
# Increase timeout (default: 300s)
COMFY_STARTUP_TIMEOUT=600
COMFY_AUTOSTART=1
```

#### **C. Memory/Resource Issues**
**Symptoms:**
- Pod crashes during model loading
- Out of memory errors

**Solution:**
```bash
# Use smaller models or increase Pod resources
# For WAN 2.1 720P FP16: Minimum 40GB RAM, 35GB storage
```

### **2. FastAPI Deprecation Warnings**

**Error Message:**
```
DeprecationWarning: on_event is deprecated, use lifespan event handlers instead
```

**Status:** ✅ **FIXED in v1.1.0**
- Updated to modern FastAPI lifespan events
- No action required with latest image

### **3. Model Download Failures**

#### **A. CivitAI Authentication**
**Error:** `403 Forbidden` or `401 Unauthorized`

**Solution:**
```bash
# Verify token in .env file
CIVITAI_TOKEN=your_actual_token_here

# Test token validity
curl -H "Authorization: Bearer $CIVITAI_TOKEN" \
  "https://civitai.com/api/v1/models"
```

#### **B. Insufficient Storage**
**Error:** `No space left on device`

**Solution:**
- WAN 2.1 720P FP16 requires 35GB+ free space
- Use smaller quantized models (FP8: 17GB, GGUF: 8GB)
- Clean up temporary files: `rm -rf /tmp/*`

#### **C. Network Timeouts**
**Error:** `Connection timeout` or `Read timeout`

**Solution:**
```bash
# Large model downloads can take 20+ minutes
# Increase timeout in download script
# Monitor progress via Pod logs
```

## 🔧 Debugging Steps

### **1. Check Pod Health**
```bash
curl https://your-pod-url/healthz
```
**Expected Response:**
```json
{
  "ok": true,
  "model_dir": "/workspace/models",
  "server_public_key_b64": "..."
}
```

### **2. Enable Debug Logging**
```bash
# Pod environment variables
LOG_LEVEL=DEBUG
LOG_SILENT=0
```

### **3. Monitor ComfyUI Process**
```bash
# SSH into Pod
ps aux | grep comfy
tail -f /opt/ComfyUI/comfyui.log
```

### **4. Check Model Directory**
```bash
curl https://your-pod-url/models/ls
```

## 🛠 Recovery Procedures

### **Pod Completely Unresponsive**
1. **Restart Pod** via RunPod console
2. **Check environment variables** - ensure all required vars are set
3. **Try DRY_RUN mode** to test without ComfyUI:
   ```bash
   DRY_RUN=1
   ```
4. **Use previous working image** if v1.1.0 fails:
   ```bash
   ghcr.io/luisvdataintelligence/comfyui_encrypted_docker:v1.0.0
   ```

### **Model Files Corrupted**
1. **Re-download models:**
   ```bash
   ./test_civitai_download.sh https://your-pod-url
   ```
2. **Verify file integrity:**
   ```bash
   ls -la /workspace/models/unet/
   file /workspace/models/unet/*.safetensors
   ```

### **Workflow Execution Fails**
1. **Check model filenames** match workflow exactly
2. **Verify input images** are accessible
3. **Test with minimal workflow** first
4. **Monitor resource usage** during execution

## 📋 Pre-Deployment Checklist

### **Environment Variables**
- [ ] `LAUNCH_MODE=api` (for Pod mode)
- [ ] `WORKER_PRIVATE_KEY_B64=<your_key>`
- [ ] `COMFYUI_MODEL_DIR=/workspace/models`
- [ ] `FORCE_CPU=1` (if no GPU)
- [ ] `COMFY_STARTUP_TIMEOUT=600`

### **Pod Configuration**
- [ ] Container image: `v1.1.0` or later
- [ ] Port 8000 exposed
- [ ] Persistent volume mounted at `/workspace/models`
- [ ] Minimum 40GB RAM for 720P models
- [ ] Minimum 35GB storage for model files

### **Network Access**
- [ ] Pod URL accessible
- [ ] `/healthz` endpoint responds
- [ ] CivitAI download URLs reachable
- [ ] GitHub container registry accessible

## 🔄 Known Working Configurations

### **CPU-Only Pod (Recommended for Testing)**
```bash
LAUNCH_MODE=api
API_PORT=8000
FORCE_CPU=1
LOG_LEVEL=INFO
COMFY_STARTUP_TIMEOUT=600
COMFYUI_MODEL_DIR=/workspace/models
WORKER_PRIVATE_KEY_B64=<your_key>
```

### **GPU Pod (Production)**
```bash
LAUNCH_MODE=api
API_PORT=8000
DEVICE_MODE=auto
LOG_LEVEL=ERROR
LOG_SILENT=1
COMFY_STARTUP_TIMEOUT=300
COMFYUI_MODEL_DIR=/workspace/models
WORKER_PRIVATE_KEY_B64=<your_key>
```

## 📞 Emergency Contacts

- **GitHub Issues**: https://github.com/LuisVDataIntelligence/comfyui_encrypted_docker/issues
- **Session Notes**: `SESSION_NOTES.md`
- **Container Registry**: https://github.com/LuisVDataIntelligence/comfyui_encrypted_docker/pkgs/container/comfyui_encrypted_docker

---
*Last Updated: September 23, 2025*