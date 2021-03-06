#######################
### Load model
#######################
import numpy
import lasagne
from lasagne_train_lvq import build_model, load_data, iterate_minibatches
import theano
import theano.tensor as tensor


x = tensor.tensor4('x')
y = tensor.imatrix('y')
flat_y = tensor.flatten(y, outdim=1)

network = build_model(x)

test_out = lasagne.layers.get_output(network, deterministic=True)

lamb = theano.shared(numpy.float32(5.0))
from sng import SNG, initialize_prototypes
sng = SNG(10, 100, gamma=2.25, lamb=lamb)
D, test_loss, test_misclass = sng.propagate(test_out, flat_y)

with numpy.load('/Tmp/devries/lvq_nonlin_raw.npz') as f:
    param_values = [f['arr_%d' % i] for i in range(len(f.files))]
    lasagne.layers.set_all_param_values(network, param_values[:-1])
    sng.W.set_value(param_values[-1])

X_train, y_train, X_val, y_val, X_test, y_test = load_data()
print X_train.min()
print X_train.max()

val_fn = theano.function([x, y], [test_loss, test_misclass])

#val_nll = 0.0
#val_err = 0.0
#val_batches = 0
#for batch in iterate_minibatches(X_train, y_train, 500, shuffle=False):
    #inputs, targets = batch
    #nll, err = val_fn(inputs, targets)
    #val_nll += nll
    #val_err += err 
    #val_batches += 1

#print("  validation loss:\t\t{:.6f}".format(val_nll / val_batches))
#print("  validation error:\t\t{:.6f} %".format(val_err*100 / val_batches))

##################
### Adversarial
##################

#epsilon = .05
#num_adv = numpy.zeros((10,))
#adv_confidences = numpy.array([])

f_dist = theano.function([x], D)
#grad = tensor.grad(test_loss, x)

#f_grad = theano.function([x, y], grad)

#for batch in iterate_minibatches(X_test, y_test, 100, shuffle=False):
    #prediction = numpy.argmin(f_dist(batch[0]), axis=1)
    
    #g = f_grad(batch[0], batch[1])
    #g = numpy.sign(g)
    #adv_x = batch[0] + epsilon*g
    
    #adv_dist = f_dist(adv_x)
    #adv_pred = numpy.argmin(adv_dist, axis=1)
    #adv_sorted_dist = numpy.sort(adv_dist, axis=1)
    #adv_conf = -1.0*(adv_sorted_dist[:, 0] - adv_sorted_dist[:, 1])/(adv_sorted_dist[:, 0] + adv_sorted_dist[:, 1])
    #for p1, p2, conf in zip(prediction, adv_pred, adv_conf):
        #if p1 != p2:
            #adv_confidences = numpy.append(adv_confidences, -conf)
            #num_adv[p1] += 1
        #else:
            #adv_confidences = numpy.append(adv_confidences, conf)
                
#print num_adv
#print numpy.sum(num_adv)
#print numpy.mean(adv_confidences)

n=10
prototypes = numpy.random.uniform(low=0.0, high=1.0, size=(10, 32, 32, 3))
mask = tensor.fmatrix()
print f_dist(numpy.float32(X_test[n, :, :, :].reshape(1, 3, 32, 32)))
for j in range(10):
    mask_ = numpy.zeros((1, 10))
    mask_[0, j] = 1.0
    mask_ = mask_.astype('float32')
    d_correct = D[0, j]
    d_incorrect = (D + mask*1e25).min()
    cost = (d_correct - d_incorrect)/(d_correct + d_incorrect)
    g_D = theano.grad(d_correct, x)
    f_D = theano.function([x], g_D)
    f_conf = theano.function([x, mask], [d_correct, cost])

    #start_x = numpy.ones((1, 1, 28, 28)).astype('float32')
    #start_x = numpy.random.uniform(low=-1.0, high=1.0, size=(1, 3, 32, 32)).astype('float32')
    succ = 0.0
    for lr in [1e5, 1e4, 1e6, 1e3]:
        if succ == 0.0:
            start_x = numpy.float32(X_test[n, :, :, :].reshape((1, 3, 32, 32)))
            init_x = start_x
            mom = numpy.zeros((1, 3, 32, 32))
   
            for i in range(250):
                dc, conf = f_conf(start_x, mask_)
                if conf < -0.8:
                    succ = 1.0
                    print i
                    break
                g = f_D(start_x)
                mom = -lr * g + 0.9*mom
                start_x += numpy.float32(mom)
                start_x = numpy.maximum(numpy.maximum(start_x, init_x-5.0), 0.0)
                start_x = numpy.minimum(numpy.minimum(start_x, init_x+5.0), 255.0)
            print dc, conf
    prototypes[j, :, :, :] = start_x.transpose([0, 2, 3, 1]).reshape((32, 32, 3))
    
  
def dispims_color(M, border=0, bordercolor=[0.0, 0.0, 0.0], *imshow_args, **imshow_keyargs):
    """ Display an array of rgb images. 

    The input array is assumed to have the shape numimages x numpixelsY x numpixelsX x 3
    """
    import pylab
    bordercolor = numpy.array(bordercolor)[None, None, :]
    numimages = len(M)
    M = M.copy()
    for i in range(M.shape[0]):
        M[i] -= M[i].flatten().min()
        M[i] /= M[i].flatten().max()
    height, width, three = M[0].shape
    assert three == 3
    n0 = 5#numpy.int(numpy.ceil(numpy.sqrt(numimages)))
    n1 = 2#numpy.int(numpy.ceil(numpy.sqrt(numimages)))
    im = numpy.array(bordercolor)*numpy.ones(
                             ((height+border)*n1+border,(width+border)*n0+border, 1),dtype='<f8')
    for i in range(n0):
        for j in range(n1):
            if i*n1+j < numimages:
                im[j*(height+border)+border:(j+1)*(height+border)+border,
                   i*(width+border)+border:(i+1)*(width+border)+border,:] = numpy.concatenate((
                  numpy.concatenate((M[i*n1+j,:,:,:],
                         bordercolor*numpy.ones((height,border,3),dtype=float)), 1),
                  bordercolor*numpy.ones((border,width+border,3),dtype=float)
                  ), 0)
    imshow_keyargs["interpolation"]="nearest"
    pylab.imshow(im, *imshow_args, **imshow_keyargs)
    pylab.savefig('lvq_adversarial_'+str(n)+'.png', bbox_inches='tight')
    
dispims_color(prototypes)
