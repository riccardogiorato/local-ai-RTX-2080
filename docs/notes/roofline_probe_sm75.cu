// Roofline probe: what fraction of the memory bus can a saturating reader
// actually pull on this TU104 (SM75), vs the spec 448 GB/s?
// Usage: ./roofline_probe [bytes_MB]  (default ~1 GiB per pass)
#include <cstdio>
#include <cuda_runtime.h>

__global__ void read_kernel(const float4 * __restrict__ src, size_t n4, float * sink) {
    float4 acc = make_float4(0,0,0,0);
    size_t i = blockIdx.x * (size_t) blockDim.x + threadIdx.x;
    const size_t stride = (size_t) gridDim.x * blockDim.x;
    for (; i < n4; i += stride) {
        const float4 v = __ldcs(src + i);  // streaming load, bypass L2 persistence
        acc.x += v.x; acc.y += v.y; acc.z += v.z; acc.w += v.w;
    }
    if (acc.x == -1.0f && acc.y == -1.0f) *sink = acc.z + acc.w;  // never true; keeps loads alive
}

int main(int argc, char ** argv) {
    const size_t mb = argc > 1 ? (size_t) atoi(argv[1]) : 1024;
    const size_t bytes = mb * 1024 * 1024;
    const size_t n4 = bytes / 16;

    cudaDeviceProp prop; cudaGetDeviceProperties(&prop, 0);
    printf("device: %s, sm%d.%d, SMs=%d,  L2=%d MB\n",
           prop.name, prop.major, prop.minor, prop.multiProcessorCount,
           448.0f,
           (int)(prop.l2CacheSize >> 20));

    float4 * src; cudaMalloc(&src, bytes);
    cudaMemset(src, 1, bytes);
    float * sink; cudaMalloc(&sink, 4);

    const int threads = 256;
    int blocks = prop.multiProcessorCount * 32;
    cudaEvent_t a, b; cudaEventCreate(&a); cudaEventCreate(&b);

    // warmup
    read_kernel<<<blocks, threads>>>(src, n4, sink);
    cudaDeviceSynchronize();

    for (int rep = 0; rep < 3; ++rep) {
        cudaEventRecord(a);
        read_kernel<<<blocks, threads>>>(src, n4, sink);
        cudaEventRecord(b);
        cudaEventSynchronize(b);
        float ms; cudaEventElapsedTime(&ms, a, b);
        printf("pass %d: %.1f ms for %zu MiB = %.1f GB/s\n", rep, ms, mb, bytes / (ms * 1e-3) / 1e9);
    }
    printf("sink %f\n", sink ? 0.f : 0.f);
    return 0;
}